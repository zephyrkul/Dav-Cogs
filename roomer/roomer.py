from redbot.core import commands, Config, checks
import discord
from redbot.core.i18n import Translator, cog_i18n
from typing import Optional
from random import choice
import string

_ = Translator("Roomer", __file__)


@cog_i18n(_)
class Roomer(commands.Cog):
    """Multiple VC tools"""

    def __init__(self):
        self.config = Config.get_conf(self, identifier=300620201743, force_registration=True)
        default_guild = {
            "category": None,
            "name": "general",
            "auto": False,
            "pstart": None,
            "pcat": None,
            "pchannels": {},
            "private": False,
        }
        self.config.register_guild(**default_guild)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        settings = await self.config.guild(member.guild).all()
        if settings["auto"]:  # Autoroom stuff
            dellist = []
            for vc in member.guild.get_channel(settings["category"]).voice_channels:
                if not vc.members:
                    dellist.append(vc)
            if len(dellist) > 1:
                dellist.remove(dellist[0])
                for vc in dellist:
                    await vc.delete(reason=_("Channel empty."))
            channel_needed = True
            for vc in member.guild.get_channel(settings["category"]).voice_channels:
                if not vc.members:
                    channel_needed = False
            if channel_needed:
                await member.guild.create_voice_channel(
                    name=settings["name"],
                    category=member.guild.get_channel(settings["category"]),
                    reason=_("A channel is needed."),
                )
        if settings["private"]:
            if before.channel:
                if before.channel.id in settings["pchannels"].values():
                    if len(before.channel.members) == 0:
                        for key in settings["pchannels"]:
                            if settings["pchannels"][key] == before.channel.id:
                                ckey = key
                        del settings["pchannels"][ckey]
                        await self.config.guild(member.guild).pchannels.set(settings["pchannels"])
                        await before.channel.delete(reason=_("Private room empty."))

    @checks.admin()
    @commands.group()
    async def roomer(self, ctx):
        """Roomer settings"""
        pass

    @commands.group()
    async def vc(self, ctx):
        """Voicechannel commands."""
        pass

    # region auto
    @roomer.group()
    async def auto(self, ctx):
        """Automation settings."""
        pass

    @auto.command()
    async def enable(self, ctx):
        """Enable automatic voicechannel creation."""
        settings = await self.config.guild(ctx.guild).all()
        # Create a VC in case none exist.
        try:
            if not ctx.guild.get_channel(settings["category"]).voice_channels:
                await ctx.guild.create_voice_channel(
                    name=settings["name"],
                    category=ctx.guild.get_channel(settings["category"]),
                    reason=_("No channels exist. We need one for people to join though."),
                )
            await self.config.guild(ctx.guild).auto.set(True)
            await ctx.send(_("Automatic voicechannel creation enabled."))
        except:
            await ctx.send(
                _(
                    "Make sure you set a category with {command} and have at least one voicechannel in it."
                ).format(command=f"``{ctx.clean_prefix}roomer auto category [category-ID]``")
            )

    @auto.command()
    async def disable(self, ctx):
        """Disable automatic voicechannel creation."""
        await self.config.guild(ctx.guild).auto.set(True)
        await ctx.send(_("Automatic voicechannel creation disabled."))

    @auto.command()
    async def name(self, ctx, *, name: str):
        """Set the name that is used for automatically created voicechannels."""
        await self.config.guild(ctx.guild).name.set(name)
        await ctx.send(
            _("Automatically created voicechannels will now be named ``{name}``.").format(
                name=name
            )
        )

    @auto.command()
    async def category(self, ctx, *, category: discord.CategoryChannel):
        """Set the category used for automatic voicechannels."""
        await self.config.guild(ctx.guild).category.set(category.id)
        await ctx.send(
            _("Category used for automatic voicechannels set to: {category}").format(
                category=category.name
            )
        )

    # endregion auto

    # region private
    @roomer.group()
    async def private(self, ctx):
        """Change settings for private rooms"""
        pass

    @private.command(name="enable")
    async def penable(self, ctx):
        """Enable private rooms"""
        if await self.config.guild(ctx.guild).pstart():
            await self.config.guild(ctx.guild).private.set(True)
            await ctx.send(_("Private channels enabled."))
        else:
            await ctx.send(
                _("Set up a starting channel using {command} first.").format(
                    command=f"``{ctx.clean_prefix}roomer private startchannel``"
                )
            )

    @private.command(name="disable")
    async def pdisable(self, ctx):
        """Disable private rooms"""
        await self.config.guild(ctx.guild).private.set(False)
        await ctx.send(_("Private channels disabled."))

    @private.command()
    async def startchannel(self, ctx, vc: discord.VoiceChannel):
        """Set a channel that users will join to start using private rooms.\nI recommend not allowing talking permissions here."""
        await self.config.guild(ctx.guild).pstart.set(vc.id)
        await self.config.guild(ctx.guild).pcat.set(vc.category_id)
        await ctx.send(
            _(
                "Private starting channel set. Users can join this channel to use all features of private rooms.\nI recommend not allowing members to speak in this channel."
            )
        )

    @vc.command()
    async def create(self, ctx, public: Optional[bool] = False, *, name: str):
        """Create a private voicechannel."""
        data = await self.config.guild(ctx.guild).all()
        if data["private"]:
            if ctx.author.voice.channel.id == data["pstart"]:
                key = "".join(choice(string.ascii_lowercase + "0123456789") for i in range(8))
                if key in data["pchannels"]:
                    key = "".join(
                        choice(string.ascii_lowercase + "0123456789") for i in range(16)
                    )  # Yes I know this can still cause conflicts. But falling back to a larger number of chars will decrease the likelihood dramatically.
                try:
                    await ctx.author.send(
                        _(
                            "The key to your private room is: ``{key}``\nGive this key to a friend and ask them to use ``{command}`` to join your private room."
                        ).format(key=key, command=f"{ctx.clean_prefix}vc join {key}")
                    )
                except discord.Forbidden:
                    await ctx.send(
                        _("Couldn't send the key to your private channel via DM. Aborting...")
                    )
                    return
                if public:
                    ov = {
                        ctx.author: discord.PermissionOverwrite(
                            view_channel=True, connect=True, speak=True, manage_channels=True
                        )
                    }
                else:
                    ov = {
                        ctx.guild.default_role: discord.PermissionOverwrite(
                            view_channel=False, connect=False
                        ),
                        ctx.author: discord.PermissionOverwrite(
                            view_channel=True, connect=True, speak=True, manage_channels=True
                        ),
                    }
                c = await ctx.guild.create_voice_channel(
                    name,
                    overwrites=ov,
                    category=ctx.guild.get_channel(data["pcat"]),
                    reason=_("Private room"),
                )
                await ctx.author.move_to(c, reason=_("Private channel."))
                data["pchannels"][key] = c.id
                await self.config.guild(ctx.guild).pchannels.set(data["pchannels"])
            else:
                await ctx.send(
                    _("You must be in the voicechannel {vc} first.").format(
                        vc=ctx.guild.get_channel(data["pstart"]).mention
                    )
                )
        else:
            await ctx.send(_("Private rooms are not enabled on this server."))

    @vc.command()
    async def join(self, ctx, key: str):
        """Join a private room."""
        await ctx.message.delete()
        async with ctx.typing():
            data = await self.config.guild(ctx.guild).all()
            if data["private"]:
                if ctx.author.voice.channel.id == data["pstart"]:
                    if key in data["pchannels"]:
                        await ctx.author.move_to(ctx.guild.get_channel(data["pchannels"][key]))
                else:
                    await ctx.send(
                        _("You must be in the voicechannel {vc} first.").format(
                            vc=ctx.guild.get_channel(data["pstart"]).mention
                        )
                    )
            else:
                await ctx.send(_("Private rooms are not enabled on this server."))

    # endregion private
