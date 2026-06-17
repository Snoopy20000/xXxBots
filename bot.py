import discord
from discord.ext import commands
from discord import Embed
from discord.app_commands import describe
import asyncio
import os
import random
import datetime
import aiohttp
from flask import Flask
import threading

# ===================== CONFIG =====================
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "MTQ4NDAwMjgxNTYyOTMzMjY3MA.GvyUMo.GiDfDSPLF81pPQROkwS1LR_PfocLr9MQat6zaM")
OWNER_ID = int(os.environ.get("OWNER_ID", "1516223700402176072"))
WELCOME_CHANNEL_ID = int(os.environ.get("WELCOME_CHANNEL_ID", "1515910056879587458"))
COMMAND_PREFIX = os.environ.get("COMMAND_PREFIX", "!")
BOT_COLOR = 0x9B59B6
BOT_FOOTER = "xXx Bot | Made with love for LO"
WEBHOOK_URL = "https://discord.com/api/webhooks/1516837949583396936/p9zxLzooxrr2IJAL3vyQwTnyG4D4KpFdIs_HFChSJCpON6zAO1QevQrNlDBsuYzkKzPK"
CONTROLLER_ROLE_ID = 1516223700402176072

# ===================== WEB SERVER (keeps Wispbyte alive) =====================
web_app = Flask(__name__)

@web_app.route("/")
def home():
    return "xXx Bot is online! Made for LO"

@web_app.route("/health")
def health():
    return {"status": "ok", "bot": "xXx", "guilds": len(bot.guilds) if bot else 0}

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

web_thread = threading.Thread(target=run_web, daemon=True)
web_thread.start()

# ===================== LOGGER =====================
class WebhookLogger:
    def __init__(self):
        self.session = None

    async def _get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def log(self, title, description, color=0x9B59B6, fields=None):
        try:
            session = await self._get_session()
            embed = {
                "title": title,
                "description": description,
                "color": color,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "footer": {"text": "xXx Bot | Activity Log"}
            }
            if fields:
                embed["fields"] = fields
            await session.post(WEBHOOK_URL, json={"embeds": [embed]})
        except:
            pass

    async def log_command(self, ctx, cmd, args=None):
        await self.log("Command: {}".format(cmd), "By {} in {}".format(ctx.author, ctx.guild.name), fields=[
            {"name": "User", "value": str(ctx.author), "inline": True},
            {"name": "Guild", "value": ctx.guild.name, "inline": True}
        ])

    async def log_admin(self, action, admin, target=None):
        await self.log("Admin: {}".format(action), "By {}".format(admin))

    async def log_welcome(self, member, guild):
        await self.log("Member Joined", "{} joined {}".format(member.name, guild.name), color=0x00FF00)

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

logger = WebhookLogger()

# ===================== MUSIC PLAYER =====================
try:
    import yt_dlp as youtube_dl
    YTDLP_AVAILABLE = True
except:
    YTDLP_AVAILABLE = False

YTDLP_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

class SimpleMusicPlayer:
    def __init__(self):
        self.players = {}

    def get_player(self, guild_id):
        if guild_id not in self.players:
            self.players[guild_id] = {
                'queue': [], 'current': None, 'volume': 0.5,
                'loop': False, 'voice_client': None, 'playing': False
            }
        return self.players[guild_id]

    async def extract_info(self, query):
        if not YTDLP_AVAILABLE:
            return None
        ydl = youtube_dl.YoutubeDL(YTDLP_OPTIONS)
        try:
            if not query.startswith('http'):
                query = "ytsearch:{}".format(query)
            info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(query, download=False))
            if 'entries' in info:
                info = info['entries'][0]
            return {
                'title': info.get('title', 'Unknown'),
                'url': info.get('url') or info.get('webpage_url'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', 'Unknown'),
                'webpage_url': info.get('webpage_url', ''),
                'source_url': info.get('url', '')
            }
        except:
            return None

    async def play_song(self, guild_id, song_info):
        player = self.get_player(guild_id)
        vc = player['voice_client']
        if not vc or not vc.is_connected():
            return False

        def after_playing(error):
            if error:
                print("Player error: {}".format(error))
            asyncio.run_coroutine_threadsafe(self._play_next(guild_id), bot.loop)

        try:
            source = discord.FFmpegPCMAudio(song_info['source_url'], **FFMPEG_OPTIONS)
            vc.play(source, after=after_playing)
            vc.source = discord.PCMVolumeTransformer(vc.source, volume=player['volume'])
            player['current'] = song_info
            player['playing'] = True
            return True
        except:
            return False

    async def _play_next(self, guild_id):
        player = self.get_player(guild_id)
        if player['loop'] and player['current']:
            await self.play_song(guild_id, player['current'])
            return
        if player['queue']:
            next_song = player['queue'].pop(0)
            await self.play_song(guild_id, next_song)
        else:
            player['current'] = None
            player['playing'] = False
            await asyncio.sleep(300)
            vc = player['voice_client']
            if vc and vc.is_connected() and not player['playing']:
                await vc.disconnect()
                player['voice_client'] = None

    async def add_to_queue(self, guild_id, song_info):
        player = self.get_player(guild_id)
        player['queue'].append(song_info)
        return len(player['queue'])

    async def skip(self, guild_id):
        player = self.get_player(guild_id)
        vc = player['voice_client']
        if vc and vc.is_playing():
            vc.stop()
            return True
        return False

    async def stop(self, guild_id):
        player = self.get_player(guild_id)
        vc = player['voice_client']
        if vc:
            vc.stop()
        player['queue'] = []
        player['current'] = None
        player['playing'] = False
        return True

    async def pause(self, guild_id):
        player = self.get_player(guild_id)
        vc = player['voice_client']
        if vc and vc.is_playing():
            vc.pause()
            return True
        return False

    async def resume(self, guild_id):
        player = self.get_player(guild_id)
        vc = player['voice_client']
        if vc and vc.is_paused():
            vc.resume()
            return True
        return False

    async def set_volume(self, guild_id, volume):
        player = self.get_player(guild_id)
        volume = max(0, min(100, volume)) / 100
        player['volume'] = volume
        vc = player['voice_client']
        if vc and vc.source:
            vc.source.volume = volume
        return volume * 100

    async def toggle_loop(self, guild_id):
        player = self.get_player(guild_id)
        player['loop'] = not player['loop']
        return player['loop']

    async def get_queue(self, guild_id):
        player = self.get_player(guild_id)
        return {
            'current': player['current'], 'queue': player['queue'],
            'volume': int(player['volume'] * 100), 'loop': player['loop'], 'playing': player['playing']
        }

    async def shuffle(self, guild_id):
        import random
        player = self.get_player(guild_id)
        random.shuffle(player['queue'])
        return True

music_player = SimpleMusicPlayer()

# ===================== BOT SETUP =====================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True
intents.presences = True
intents.guilds = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, case_insensitive=True, help_command=None)

# ===================== WELCOME =====================
WELCOME_MESSAGES = [
    "**{}** just landed in **{}**! Everyone say hi!",
    "Watch out! **{}** has entered **{}**!",
    "A wild **{}** appeared in **{}**!",
    "**{}** just joined the family at **{}**! Welcome!",
]

@bot.event
async def on_member_join(member):
    guild = member.guild
    await logger.log_welcome(member, guild)

    channel = guild.get_channel(WELCOME_CHANNEL_ID)
    if not channel:
        for ch in guild.text_channels:
            if "welcome" in ch.name.lower():
                channel = ch
                break
    if not channel:
        return

    embed = Embed(
        title="Welcome to {}!".format(guild.name),
        description=random.choice(WELCOME_MESSAGES).format(member.mention, guild.name),
        color=BOT_COLOR
    )
    embed.add_field(name="Member Info", value="Name: {} | ID: `{}`".format(member.name, member.id), inline=True)
    embed.add_field(name="Account Age", value="<t:{}:R>".format(int(member.created_at.timestamp())), inline=True)
    embed.add_field(name="Member Count", value="You are member **#{}**!".format(guild.member_count), inline=True)
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    embed.set_footer(text=BOT_FOOTER)
    await channel.send(embed=embed)

# ===================== MUSIC COMMANDS =====================
@bot.hybrid_command(name="join", description="Join a voice channel")
async def join(ctx):
    if not ctx.author.voice:
        return await ctx.send(embed=Embed(title="Error", description="Join a voice channel first!", color=0xFF0000))
    channel = ctx.author.voice.channel
    if ctx.voice_client:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect()
    music_player.get_player(ctx.guild.id)['voice_client'] = ctx.voice_client
    await ctx.send(embed=Embed(title="Joined", description="Connected to **{}**".format(channel.name), color=BOT_COLOR))

@bot.hybrid_command(name="leave", description="Leave voice channel")
async def leave(ctx):
    if not ctx.voice_client:
        return await ctx.send(embed=Embed(title="Error", description="Not in a voice channel!", color=0xFF0000))
    await music_player.stop(ctx.guild.id)
    await ctx.voice_client.disconnect()
    await ctx.send(embed=Embed(title="Left", description="Disconnected", color=BOT_COLOR))

@bot.hybrid_command(name="play", description="Play a song")
@describe(query="Song name or URL")
async def play(ctx, *, query: str):
    if not ctx.author.voice:
        return await ctx.send(embed=Embed(title="Error", description="Join a voice channel first!", color=0xFF0000))
    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()
        music_player.get_player(ctx.guild.id)['voice_client'] = ctx.voice_client

    msg = await ctx.send("**Searching...**")
    song = await music_player.extract_info(query)
    if not song:
        return await msg.edit(embed=Embed(title="Error", description="Song not found!", color=0xFF0000))

    player = music_player.get_player(ctx.guild.id)
    if not player['playing']:
        await music_player.play_song(ctx.guild.id, song)
        embed = Embed(title="Now Playing", description="**[{}]({})**".format(song['title'], song['webpage_url']), color=BOT_COLOR)
        embed.add_field(name="Artist", value=song['uploader'], inline=True)
        embed.add_field(name="Duration", value="{}:{:02d}".format(song['duration']//60, song['duration']%60), inline=True)
        if song['thumbnail']:
            embed.set_thumbnail(url=song['thumbnail'])
        embed.set_footer(text=BOT_FOOTER)
        await msg.edit(embed=embed)
    else:
        pos = await music_player.add_to_queue(ctx.guild.id, song)
        embed = Embed(title="Added to Queue", description="**[{}]({})**".format(song['title'], song['webpage_url']), color=BOT_COLOR)
        embed.add_field(name="Position", value="#{}".format(pos), inline=True)
        await msg.edit(embed=embed)

@bot.hybrid_command(name="skip", description="Skip current song")
async def skip(ctx):
    success = await music_player.skip(ctx.guild.id)
    await ctx.send(embed=Embed(title="Skipped" if success else "Error", 
        description="Skipped!" if success else "Nothing playing!", 
        color=BOT_COLOR if success else 0xFF0000))

@bot.hybrid_command(name="stop", description="Stop playback")
async def stop(ctx):
    await music_player.stop(ctx.guild.id)
    await ctx.send(embed=Embed(title="Stopped", description="Playback stopped", color=BOT_COLOR))

@bot.hybrid_command(name="pause", description="Pause music")
async def pause(ctx):
    success = await music_player.pause(ctx.guild.id)
    await ctx.send(embed=Embed(title="Paused" if success else "Error", 
        description="Paused!" if success else "Nothing playing!",
        color=BOT_COLOR if success else 0xFF0000))

@bot.hybrid_command(name="resume", description="Resume music")
async def resume(ctx):
    success = await music_player.resume(ctx.guild.id)
    await ctx.send(embed=Embed(title="Resumed" if success else "Error",
        description="Resumed!" if success else "Nothing paused!",
        color=BOT_COLOR if success else 0xFF0000))

@bot.hybrid_command(name="queue", description="Show queue")
async def queue(ctx):
    data = await music_player.get_queue(ctx.guild.id)
    embed = Embed(title="Music Queue", color=BOT_COLOR)
    if data['current']:
        embed.add_field(name="Now Playing", value=data['current']['title'], inline=False)
    else:
        embed.add_field(name="Now Playing", value="Nothing", inline=False)
    embed.add_field(name="Queue", value="{} songs".format(len(data['queue'])), inline=True)
    embed.add_field(name="Volume", value="{}%".format(data['volume']), inline=True)
    embed.add_field(name="Loop", value="On" if data['loop'] else "Off", inline=True)
    embed.set_footer(text=BOT_FOOTER)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="volume", description="Set volume 0-100")
@describe(vol="Volume level")
async def volume(ctx, vol: int):
    new_vol = await music_player.set_volume(ctx.guild.id, vol)
    await ctx.send(embed=Embed(title="Volume", description="Set to **{}%**".format(int(new_vol)), color=BOT_COLOR))

@bot.hybrid_command(name="loop", description="Toggle loop")
async def loop(ctx):
    status = await music_player.toggle_loop(ctx.guild.id)
    await ctx.send(embed=Embed(title="Loop", description="Now **{}**".format('ON' if status else 'OFF'), color=BOT_COLOR))

@bot.hybrid_command(name="shuffle", description="Shuffle queue")
async def shuffle(ctx):
    await music_player.shuffle(ctx.guild.id)
    await ctx.send(embed=Embed(title="Shuffled", description="Queue shuffled!", color=BOT_COLOR))

# ===================== ADMIN COMMANDS =====================
def is_controller(ctx):
    role = discord.utils.get(ctx.guild.roles, id=CONTROLLER_ROLE_ID)
    if role and role in ctx.author.roles:
        return True
    return ctx.author.guild_permissions.administrator or ctx.author.id == OWNER_ID

@bot.hybrid_command(name="kick", description="Kick a member")
async def kick(ctx, member: discord.Member, *, reason=None):
    if not is_controller(ctx):
        return await ctx.send(embed=Embed(title="Error", description="No permission!", color=0xFF0000))
    await member.kick(reason=reason)
    await ctx.send(embed=Embed(title="Kicked", description="**{}** kicked!".format(member.name), color=BOT_COLOR))
    await logger.log_admin("Kick", ctx.author, member)

@bot.hybrid_command(name="ban", description="Ban a member")
async def ban(ctx, member: discord.Member, *, reason=None):
    if not is_controller(ctx):
        return await ctx.send(embed=Embed(title="Error", description="No permission!", color=0xFF0000))
    await member.ban(reason=reason)
    await ctx.send(embed=Embed(title="Banned", description="**{}** banned!".format(member.name), color=0xFF0000))
    await logger.log_admin("Ban", ctx.author, member)

@bot.hybrid_command(name="purge", description="Delete messages")
async def purge(ctx, amount: int = 10):
    if not is_controller(ctx):
        return await ctx.send(embed=Embed(title="Error", description="No permission!", color=0xFF0000))
    if amount > 100:
        amount = 100
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(embed=Embed(title="Purged", description="Deleted **{}** messages!".format(len(deleted)-1), color=BOT_COLOR))
    await asyncio.sleep(3)
    await msg.delete()

@bot.hybrid_command(name="say", description="Send message as bot")
async def say(ctx, channel: discord.TextChannel = None, *, message):
    if not is_controller(ctx):
        return await ctx.send(embed=Embed(title="Error", description="No permission!", color=0xFF0000))
    target = channel or ctx.channel
    await target.send(message)
    await ctx.message.delete()

@bot.hybrid_command(name="serverinfo", description="Server info")
async def serverinfo(ctx):
    g = ctx.guild
    embed = Embed(title="{} Info".format(g.name), color=BOT_COLOR)
    embed.add_field(name="Members", value=str(g.member_count), inline=True)
    embed.add_field(name="Channels", value="{} text | {} voice".format(len(g.text_channels), len(g.voice_channels)), inline=True)
    embed.add_field(name="Roles", value=str(len(g.roles)), inline=True)
    embed.add_field(name="Created", value="<t:{}:R>".format(int(g.created_at.timestamp())), inline=True)
    embed.set_footer(text=BOT_FOOTER)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="userinfo", description="User info")
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = Embed(title="{} Info".format(member.name), color=BOT_COLOR)
    embed.add_field(name="ID", value="`{}`".format(member.id), inline=True)
    embed.add_field(name="Joined", value="<t:{}:R>".format(int(member.joined_at.timestamp())) if member.joined_at else "Unknown", inline=True)
    embed.add_field(name="Roles", value="{} roles".format(len(member.roles)-1), inline=True)
    embed.set_footer(text=BOT_FOOTER)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="botinfo", description="Bot info")
async def botinfo(ctx):
    embed = Embed(title="xXx Bot Info", description="Music, Admin, Welcome, Web Dashboard", color=BOT_COLOR)
    embed.add_field(name="Servers", value=str(len(bot.guilds)), inline=True)
    embed.add_field(name="Users", value=str(sum(g.member_count for g in bot.guilds)), inline=True)
    embed.add_field(name="Prefix", value="`{}` or `/`".format(COMMAND_PREFIX), inline=True)
    embed.add_field(name="Music", value="/play, /skip, /queue, /pause, /resume, /volume, /loop, /shuffle", inline=False)
    embed.add_field(name="Admin", value="/kick, /ban, /purge, /say, /serverinfo, /userinfo", inline=False)
    embed.set_footer(text=BOT_FOOTER)
    await ctx.send(embed=embed)

# ===================== VIDEO STREAMING =====================
@bot.hybrid_command(name="video", description="Play audio from video URL")
@describe(url="YouTube video or direct video URL")
async def video(ctx, *, url: str):
    if not ctx.author.voice:
        return await ctx.send(embed=Embed(title="Error", description="Join a voice channel!", color=0xFF0000))
    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()
        music_player.get_player(ctx.guild.id)['voice_client'] = ctx.voice_client

    msg = await ctx.send("**Loading video...**")
    vid = await music_player.extract_info(url)
    if not vid:
        return await msg.edit(embed=Embed(title="Error", description="Video not found!", color=0xFF0000))

    player = music_player.get_player(ctx.guild.id)
    if not player['playing']:
        await music_player.play_song(ctx.guild.id, vid)
        embed = Embed(title="Video Playing", description="**[{}]({})**".format(vid['title'], vid['webpage_url']), color=0xFF6600)
        if vid['thumbnail']:
            embed.set_thumbnail(url=vid['thumbnail'])
        embed.set_footer(text=BOT_FOOTER)
        await msg.edit(embed=embed)
    else:
        pos = await music_player.add_to_queue(ctx.guild.id, vid)
        await msg.edit(embed=Embed(title="Video Queued", description="**[{}]({})** at #{}".format(vid['title'], vid['webpage_url'], pos), color=0xFF6600))

# ===================== EVENTS =====================
@bot.event
async def on_ready():
    print("xXx Bot online!")
    print("Logged in as: {} ({})".format(bot.user.name, bot.user.id))
    print("Guilds: {}".format(len(bot.guilds)))
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="!help | /help | xXx Bot"))
    await logger.log("Bot Started", "xXx Bot online! Guilds: {}".format(len(bot.guilds)), color=0x00FF00)
    try:
        await bot.tree.sync()
        print("Slash commands synced!")
    except:
        pass

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=Embed(title="Error", description="No permission!", color=0xFF0000))
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=Embed(title="Error", description="Missing: {}".format(error.param.name), color=0xFF0000))
    else:
        print("Error: {}".format(error))

# ===================== RUN =====================
if __name__ == "__main__":
    print("Starting xXx Bot...")
    print("Web server running on port 8080")
    bot.run(DISCORD_TOKEN)
