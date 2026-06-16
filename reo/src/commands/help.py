# help.py

import discord
from discord.ext import commands
from discord import ui

from reo.src.checks import checks

from reo.style import color
import traceback, sys

from reo.console.logging import logger

from reo.engine.Bot import AutoShardedBot


class CogInfo:
    def __init__(self, name, category, description, hidden, emoji):
        self.name = name
        self.category = category
        self.description = description
        self.hidden = hidden
        self.emoji = emoji


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot: AutoShardedBot = bot
        self.cog_info = CogInfo(
            name="Help",
            category="Extra",
            description="Help commands",
            hidden=False,
            emoji=self.bot.emoji.HELP,
        )
        self.all_app_commands = None

    @commands.hybrid_command(
        name="help",
        with_app_command=True,
        help="Zeigt alle Befehle des Bots an",
        aliases=["h"],
    )
    @checks.ignore_check()
    @checks.blacklist_check()
    @commands.cooldown(rate=10, per=60, type=commands.BucketType.user)
    async def help(self, ctx: commands.Context):
        try:
            if ctx.interaction and not ctx.interaction.response.is_done():
                await ctx.defer()
            if not self.all_app_commands:
                self.all_app_commands = await self.bot.tree.fetch_commands()
            view = HomeView(self.bot, ctx, self.all_app_commands)
            view.message = await ctx.send(view=view)
        except Exception as e:
            logger.error(
                f"Error in file {__file__} at line {traceback.extract_tb(sys.exc_info()[2])[0][1]}: {e}"
            )
            raise e


class BaseHelpView(ui.LayoutView):
    def __init__(self, bot, ctx, all_app_commands, reported=False, timeout=120):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.ctx = ctx
        self.all_app_commands = all_app_commands
        self.reported = reported
        self.message: discord.Message = None

    def get_language(self) -> str:
        if not getattr(self.ctx, "guild", None):
            return "en"
        return (
            self.bot.cache.guilds.get(str(self.ctx.guild.id), {}).get("language", "en")
            or "en"
        ).lower()

    def tr(self, english: str, german: str) -> str:
        return german

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=self.tr(
                        "You are not allowed to use this interaction",
                        "Du darfst diese Interaktion nicht verwenden",
                    ),
                    color=color.red,
                ),
                ephemeral=True,
                delete_after=10,
            )
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except (discord.NotFound, discord.HTTPException):
                pass

    def get_cogs(self):
        extra_cogs = []
        main_cogs = []
        hidden_cogs = []
        for cog_name in self.bot.cogs:
            cog = self.bot.get_cog(cog_name)
            if hasattr(cog, "cog_info") and cog.cog_info:
                if cog.cog_info.hidden:
                    hidden_cogs.append(cog)
                elif cog.cog_info.category.lower() == "main":
                    main_cogs.append(cog)
                elif cog.cog_info.category.lower() == "extra":
                    extra_cogs.append(cog)
        return main_cogs, extra_cogs, hidden_cogs

    def get_all_commands_count(self):
        count = 0
        for cog_name in self.bot.cogs:
            cog = self.bot.get_cog(cog_name)
            count += len(cog.get_commands())
        return count


class HomeView(BaseHelpView):
    def __init__(self, bot, ctx, all_app_commands, reported=False):
        super().__init__(bot, ctx, all_app_commands, reported)
        container = ui.Container()
        container.add_item(
            ui.TextDisplay(
                f"# {self.bot.user.display_name}\n-# {self.tr('Help menu', 'Hilfe-Menü')}"
            )
        )
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        prefix = self.bot.cache.guilds.get(str(self.ctx.guild.id), {}).get(
            "prefix", self.bot.BotConfig.PREFIX
        )
        desc = (
            f"- Das Prefix für diesen Server ist `{prefix}`\n"
            f"- Gesamtzahl der Befehle: `{self.get_all_commands_count()}`\n"
            f"- [REO einladen]({self.bot.urls.INVITE}) | "
            f"[Support-Server]({self.bot.urls.SUPPORT_SERVER}) | "
            f"[Vote für mich]({self.bot.urls.VOTE})"
        )
        container.add_item(ui.TextDisplay(desc))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        main_cogs, extra_cogs, _ = self.get_cogs()
        if main_cogs:
            main_desc = f"### **__{self.tr('Main', 'Haupt')}__**\n" + "\n".join(
                [
                    f"> **{cog.cog_info.emoji} : {cog.cog_info.name}**"
                    for cog in main_cogs
                ]
            )
            container.add_item(ui.TextDisplay(main_desc))
        if extra_cogs:
            extra_desc = f"### **__{self.tr('Extra', 'Erweitert')}__**\n" + "\n".join(
                [
                    f"> **{cog.cog_info.emoji} : {cog.cog_info.name}**"
                    for cog in extra_cogs
                ]
            )
            container.add_item(ui.TextDisplay(extra_desc))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(
            ui.TextDisplay(
                self.tr("## Select a category to view", "## Wähle eine Kategorie aus")
            )
        )
        container.add_item(CategorySelectRow(self))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        button_row = ui.ActionRow()
        button_row.add_item(AllCommandsButton(self.bot.emoji.COMMANDS))
        report_button = ReportButton(self.bot.emoji.ERROR, self.bot)
        if self.reported:
            report_button.disabled = True
        button_row.add_item(report_button)
        button_row.add_item(
            ui.Button(
                label=self.tr("Invite", "Einladen"),
                style=discord.ButtonStyle.link,
                url=self.bot.urls.INVITE,
                emoji=self.bot.emoji.INVITE,
            )
        )
        button_row.add_item(
            ui.Button(
                label=self.tr("Support", "Support"),
                style=discord.ButtonStyle.link,
                url=self.bot.urls.SUPPORT_SERVER,
                emoji=self.bot.emoji.SUPPORT,
            )
        )
        container.add_item(button_row)
        self.add_item(container)


class AllCommandsButton(ui.Button["BaseHelpView"]):
    def __init__(self, emoji):
        super().__init__(
            label="Alle Befehle", style=discord.ButtonStyle.green, emoji=emoji
        )

    async def callback(self, interaction: discord.Interaction):
        if not await self.view.interaction_check(interaction):
            return
        all_view = AllCommandsView(
            self.view.bot, self.view.ctx, self.view.all_app_commands, self.view.reported
        )
        all_view.message = interaction.message
        await interaction.response.edit_message(view=all_view)


class ReportButton(ui.Button["BaseHelpView"]):
    def __init__(self, emoji, bot):
        super().__init__(label="Bericht", style=discord.ButtonStyle.red, emoji=emoji)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        if not await self.view.interaction_check(interaction):
            return
        modal = ReportModal(self.bot)
        await interaction.response.send_modal(modal)
        await modal.wait()
        if modal.submitted:
            self.view.reported = True
            self.disabled = True
            await interaction.message.edit(view=self.view)


class ReportModal(ui.Modal, title="Bericht einreichen"):
    report_title_field = ui.TextInput(
        placeholder="Berichtstitel",
        label="Berichtstitel",
        required=True,
        style=discord.TextStyle.short,
    )
    report_description_field = ui.TextInput(
        placeholder="Berichtsbeschreibung",
        label="Berichtsbeschreibung",
        required=True,
        style=discord.TextStyle.long,
    )
    report_attachment_field = ui.TextInput(
        placeholder="Links mit Komma trennen",
        label="Bericht-Anhänge Links",
        required=False,
        style=discord.TextStyle.long,
    )

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.submitted = False

    async def on_submit(self, interaction: discord.Interaction):
        title = self.report_title_field.value
        description = self.report_description_field.value
        attachments = (
            self.report_attachment_field.value.split(",")
            if self.report_attachment_field.value
            else []
        )
        if not title or not description:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description="Titel und Beschreibung sind erforderlich", color=color.red
                ),
                ephemeral=True,
                delete_after=10,
            )
        embed = discord.Embed(title=title, description=description, color=color.black)
        if attachments:
            embed.add_field(
                name="Attachments links", value="\n".join(attachments), inline=False
            )
        embed.set_footer(
            text=f"Reported by {interaction.user.display_name} | {interaction.user.id}",
            icon_url=interaction.user.display_avatar.url,
        )
        embed.set_author(
            name=f"{interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url,
        )
        channel = self.bot.get_channel(self.bot.channels.report_channel)
        if channel:
            await channel.send(embed=embed)
        else:
            logger.error(
                f"Report channel not found. Channel ID: {self.bot.channels.report_channel}"
            )
        await interaction.response.send_message(
            embed=discord.Embed(
                description="Bericht erfolgreich gesendet", color=color.green
            ),
            ephemeral=True,
        )
        self.submitted = True
        self.stop()

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        logger.error(
            f"Error in file {__file__} at line {traceback.extract_tb(sys.exc_info()[2])[0][1]}: {error}"
        )


class CategorySelectRow(ui.ActionRow["HomeView"]):
    def __init__(self, view: HomeView):
        super().__init__()
        main_cogs, extra_cogs, _ = view.get_cogs()
        options = [
            discord.SelectOption(
                label=cog.cog_info.name,
                value=cog.cog_info.name.lower(),
                description=cog.cog_info.description,
                emoji=cog.cog_info.emoji,
            )
            for cog in main_cogs + extra_cogs
        ]
        select = ui.Select(
            placeholder=view.tr("Select a category to view", "Wähle eine Kategorie aus"),
            options=options,
        )
        select.callback = self.select_category
        self.add_item(select)

    async def select_category(self, interaction: discord.Interaction):
        if not await self.view.interaction_check(interaction):
            return
        cog_name = interaction.data["values"][0]
        cog = None
        for name in self.view.bot.cogs:
            if name.lower() == cog_name:
                cog = self.view.bot.get_cog(name)
                break
        if not cog:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=self.view.tr("Category not found", "Kategorie nicht gefunden"),
                    color=color.red,
                ),
                ephemeral=True,
                delete_after=10,
            )
        category_view = CategoryView(
            self.view.bot,
            self.view.ctx,
            self.view.all_app_commands,
            cog,
            self.view.reported,
        )
        category_view.message = interaction.message
        await interaction.response.edit_message(view=category_view)


class AllCommandsView(BaseHelpView):
    def __init__(self, bot, ctx, all_app_commands, reported=False):
        super().__init__(bot, ctx, all_app_commands, reported)
        container = ui.Container()
        container.add_item(ui.TextDisplay(f"# {self.tr('All Commands', 'Alle Befehle')}"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        main_cogs, extra_cogs, _ = self.get_cogs()
        for cog in main_cogs + extra_cogs:
            cmds = " | ".join(
                [f"**`{command.name}`**" for command in cog.get_commands()]
            )
            container.add_item(
                ui.TextDisplay(
                    f"**{cog.cog_info.emoji} {cog.cog_info.name} [{len(cog.get_commands())}]**\n{cmds}"
                )
            )
            container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        button_row = ui.ActionRow()
        button_row.add_item(BackButton())
        container.add_item(button_row)
        self.add_item(container)


class CategoryView(BaseHelpView):
    def __init__(self, bot, ctx, all_app_commands, cog, reported=False):
        super().__init__(bot, ctx, all_app_commands, reported)
        self.cog = cog
        container = ui.Container()
        desc = f"# {self.cog.cog_info.name} {self.tr('Commands', 'Befehle')}\n"
        all_commands = self.cog.get_commands()
        chunks = [all_commands[i : i + 5] for i in range(0, len(all_commands), 5)]
        for chunk in chunks:
            desc += (
                f"\n>  - {' | '.join([f'**`{command.name}`**' for command in chunk])}"
            )
        container.add_item(ui.TextDisplay(desc))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(
            ui.TextDisplay(
                self.tr("## Select a command to view", "## Wähle einen Befehl aus")
            )
        )
        container.add_item(CommandSelectRow(self))
        button_row = ui.ActionRow()
        button_row.add_item(BackButton())
        container.add_item(button_row)
        self.add_item(container)


class CommandSelectRow(ui.ActionRow["CategoryView"]):
    def __init__(self, view: CategoryView):
        super().__init__()
        all_commands = view.cog.get_commands()
        options = [
            discord.SelectOption(
                label=command.name, value=command.name, description=command.help
            )
            for command in all_commands
        ]
        select = ui.Select(
            placeholder=view.tr("Select a command to view", "Wähle einen Befehl aus"),
            options=options,
        )
        select.callback = self.select_command
        self.add_item(select)

    async def select_command(self, interaction: discord.Interaction):
        if not await self.view.interaction_check(interaction):
            return
        command_name = interaction.data["values"][0]
        command = None
        for cmd in self.view.cog.get_commands():
            if cmd.name == command_name:
                command = cmd
                break
        if not command:
            return await interaction.response.send_message(
                embed=discord.Embed(
                    description=self.view.tr("Command not found", "Befehl nicht gefunden"),
                    color=color.red,
                ),
                ephemeral=True,
                delete_after=10,
            )
        command_view = CommandView(
            self.view.bot,
            self.view.ctx,
            self.view.all_app_commands,
            command,
            self.view.cog,
            self.view.reported,
        )
        command_view.message = interaction.message
        await interaction.response.edit_message(view=command_view)


class CommandView(BaseHelpView):
    def __init__(self, bot, ctx, all_app_commands, command, cog, reported=False):
        super().__init__(bot, ctx, all_app_commands, reported)
        self.command = command
        self.cog = cog
        container = ui.Container()
        desc = f"# {self.command.name.capitalize()} {self.tr('Command', 'Befehl')}\n{self.command.help or ''}"
        app_command = next(
            (cmd for cmd in self.all_app_commands if cmd.name == self.command.name),
            None,
        )
        prefix = self.bot.BotConfig.PREFIX
        params = " ".join([f"<{arg}>" for arg in self.command.clean_params])
        if app_command:
            if app_command.options:
                desc += (
                    f"\n\n**{self.tr('Primary Command', 'Hauptbefehl')}:** `{prefix}{app_command.name} {params}`"
                )
                desc += f"\n\n**{self.tr('Options', 'Optionen')}:**\n"
                for option in app_command.options:
                    mention = (
                        option.mention
                        if hasattr(option, "mention")
                        else f"{prefix}{self.command.name} {option.name}"
                    )
                    desc += f"\n> {mention}\n> {option.description}\n"
            else:
                mention = (
                    app_command.mention
                    if hasattr(app_command, "mention")
                    else f"{prefix}{self.command.name}"
                )
                desc += f"\n\n**{self.tr('Primary Command', 'Hauptbefehl')}:** {mention}"
        else:
            desc += f"\n\n**{self.tr('Primary Command', 'Hauptbefehl')}:** `{prefix}{self.command.name} {params}`"
            if isinstance(self.command, commands.Group):
                desc += f"\n\n**{self.tr('Subcommands', 'Unterbefehle')}:**\n"
                for subcommand in self.command.commands:
                    sub_params = " ".join(
                        [f"<{arg}>" for arg in subcommand.clean_params]
                    )
                    desc += f"\n> **`{prefix}{self.command.name} {subcommand.name} {sub_params}`** \n> {subcommand.help}\n"
        container.add_item(ui.TextDisplay(desc))
        button_row = ui.ActionRow()
        button_row.add_item(BackButton())
        container.add_item(button_row)
        self.add_item(container)


class BackButton(ui.Button["BaseHelpView"]):
    def __init__(self):
        super().__init__(
            label="Zurück",
            style=discord.ButtonStyle.secondary,
            emoji=discord.PartialEmoji(name="back", id=1493613530719453375),
        )

    async def callback(self, interaction: discord.Interaction):
        if not await self.view.interaction_check(interaction):
            return
        if isinstance(self.view, AllCommandsView) or isinstance(
            self.view, CategoryView
        ):
            home_view = HomeView(
                self.view.bot,
                self.view.ctx,
                self.view.all_app_commands,
                self.view.reported,
            )
            home_view.message = interaction.message
            await interaction.response.edit_message(view=home_view)
        elif isinstance(self.view, CommandView):
            category_view = CategoryView(
                self.view.bot,
                self.view.ctx,
                self.view.all_app_commands,
                self.view.cog,
                self.view.reported,
            )
            category_view.message = interaction.message
            await interaction.response.edit_message(view=category_view)


async def setup(bot: AutoShardedBot):
    await bot.add_cog(Help(bot))
