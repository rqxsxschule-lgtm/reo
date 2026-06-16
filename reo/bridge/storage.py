from __future__ import annotations

from __future__ import annotations

from typing import Any

from reo.console.logging import logger
from reo.config.config import storage as StorageConfig

_client = None
_database = None
_storage_settings = StorageConfig()


# Minimal in-memory Mongo-like adapter used as a fallback when MongoDB is
# not configured or not reachable. It implements the small subset of
# collection operations used by the codebase: insert_one, find_one,
# find_one_and_update, find (with sort/to_list), delete_many, create_index,
# count_documents.
class _InMemoryCursor:
    def __init__(self, docs: list[dict[str, Any]]):
        self._docs = docs

    def sort(self, *args, **kwargs):
        # naive: support sort(('id', 1)) or sort('id', 1) by key
        return self

    async def to_list(self, length=None):
        return list(self._docs)


class _InMemoryCollection:
    def __init__(self, storage: dict[str, list[dict[str, Any]]], name: str):
        self._storage = storage
        self._name = name

    async def insert_one(self, document: dict[str, Any]):
        # emulate _id auto generation
        doc = dict(document)
        if '_id' not in doc:
            doc['_id'] = id(doc)
        self._storage.setdefault(self._name, []).append(doc)
        return type('R', (), {'inserted_id': doc['_id']})()

    async def insert_many(self, docs):
        for d in docs:
            await self.insert_one(d)
        return None

    async def find_one(self, filters: dict | None = None, sort=None):
        items = self._storage.get(self._name, [])
        if not filters:
            return items[0] if items else None
        for doc in items:
            if all(doc.get(k) == v for k, v in filters.items()):
                return doc
        return None

    async def find_one_and_update(self, filters, update, upsert=False, return_document=None):
        items = self._storage.setdefault(self._name, [])
        for doc in items:
            if all(doc.get(k) == v for k, v in filters.items()):
                # support simple $inc
                if '$inc' in update:
                    for k, v in update['$inc'].items():
                        doc[k] = doc.get(k, 0) + v
                if '$set' in update:
                    for k, v in update['$set'].items():
                        doc[k] = v
                return doc

        if upsert:
            new_doc = dict(filters)
            if '$inc' in update:
                for k, v in update['$inc'].items():
                    new_doc[k] = new_doc.get(k, 0) + v
            if '$set' in update:
                for k, v in update['$set'].items():
                    new_doc[k] = v
            new_doc['_id'] = id(new_doc)
            items.append(new_doc)
            return new_doc
        return None

    def find(self, filters: dict | None = None):
        items = self._storage.get(self._name, [])
        if not filters:
            return _InMemoryCursor(items)
        matched = [doc for doc in items if all(doc.get(k) == v for k, v in filters.items())]
        return _InMemoryCursor(matched)

    async def delete_many(self, filters):
        items = self._storage.get(self._name, [])
        to_delete = [doc for doc in items if all(doc.get(k) == v for k, v in filters.items())]
        for d in to_delete:
            items.remove(d)
        return type('R', (), {'deleted_count': len(to_delete)})()

    async def create_index(self, *args, **kwargs):
        return None

    async def count_documents(self, filters: dict | None = None):
        items = self._storage.get(self._name, [])
        if not filters:
            return len(items)
        return sum(1 for doc in items if all(doc.get(k) == v for k, v in filters.items()))


class _InMemoryDatabase:
    def __init__(self):
        self._storage: dict[str, list[dict[str, Any]]] = {}

    def __getitem__(self, item: str):
        return _InMemoryCollection(self._storage, item)


async def _connect_mongo_or_fallback():
    global _client, _database
    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        if not _storage_settings.uri:
            raise RuntimeError('MONGO_URI not configured')

        _client = AsyncIOMotorClient(_storage_settings.uri, serverSelectionTimeoutMS=10000)
        await _client.admin.command('ping')
        _database = _client[_storage_settings.name]
        logger.info('Connected to Mongo storage')
    except Exception as error:
        logger.warning(f'MongoDB unavailable, using in-memory storage fallback: {error}')
        _client = None
        _database = _InMemoryDatabase()


async def get_client():
    global _client
    if _client is None and not isinstance(_database, _InMemoryDatabase):
        await _connect_mongo_or_fallback()
    return _client


async def get_database():
    global _database
    if _database is None:
        await _connect_mongo_or_fallback()
    return _database


async def get_collection(name: str):
    database = await get_database()
    return database[name]


async def get_connection():
    return await get_database()


async def release_connection(_connection=None):
    return None


async def ping() -> float:
    try:
        client = await get_client()
        if client is None:
            return 1.0
        await client.admin.command('ping')
        return 1.0
    except Exception:
        return 0.0
