from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from reo.surface.routes import dashboard, generate, transcript
from reo.surface.runtime import bind_bot

from reo.config.config import BotConfigClass

BOT_CONFIG = BotConfigClass()
app = FastAPI(title=f"{BOT_CONFIG.NAME} Surface", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def detect_language(request: Request, call_next):
    # detect language from first path segment (e.g. /en/ or /de/)
    path = request.url.path or "/"
    first = path.lstrip("/").split("/", 1)[0] or ""
    if first in ("en", "de"):
        request.state.lang = first
        # strip the language prefix so routers still work under /dashboard
        # but also preserve original path for static files
        # we won't rewrite the path here; route handlers can read request.url.path
    else:
        request.state.lang = "en"
    response = await call_next(request)
    return response


# Include API/dashboard routers. Add language-prefixed mounts so users
# can reach the dashboard at /dashboard, /en/dashboard, and /de/dashboard.
app.include_router(transcript.router)
app.include_router(generate.router)
app.include_router(dashboard.router)
app.include_router(dashboard.router, prefix="/en")
app.include_router(dashboard.router, prefix="/de")

# Serve the static public site so /en/ and /de/ are available
app.mount("/", StaticFiles(directory="public", html=True), name="public")


@app.get("/dashboard")
async def dashboard_root():
    # default to english dashboard
    return RedirectResponse(url="/en/dashboard", status_code=303)
