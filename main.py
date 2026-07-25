import asyncio
import os
from threading import Thread

import discord
from discord.ext import commands
from flask import Flask
import yt_dlp

# --- 🌐 Keep Alive Web Server for Render ---
app = Flask('')


@app.route('/')
def home():
  return "Bot is alive and multi-platform ready!"


def run_flask():
  port = int(os.environ.get('PORT', 8080))
  app.run(host='0.0.0.0', port=port)


def keep_alive():
  t = Thread(target=run_flask)
  t.start()


# --- 🤖 Discord Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='k!', intents=intents)

FFMPEG_OPTIONS = {
    'before_options': (
        '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
    ),
    'options': '-vn',
}

# --- 🎵 Pure Non-YouTube Multi-Platform Engine ---
# Supports: SoundCloud, Bandcamp, Vimeo, Twitch, Direct Links, etc.
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'scsearch',  # Direct SoundCloud Search
    'nocheckcertificate': True,
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)


@bot.event
async def on_ready():
  print(f'✅ Bot Active: {bot.user.name}')


@bot.command(name='play')
async def play(ctx, *, search: str):
  if not ctx.author.voice:
    await ctx.send('❌ **भाई, पहले किसी Voice Channel (VC) में तो जुड़ो!**')
    return

  channel = ctx.author.voice.channel

  try:
    if ctx.voice_client is None:
      await channel.connect()
    elif ctx.voice_client.channel != channel:
      await ctx.voice_client.move_to(channel)
  except Exception as e:
    await ctx.send(f'⚠️ **VC Connection Error:** `{e}`')
    return

  msg = await ctx.send(f'🔍 **Searching SoundCloud & Platforms:** `{search}`...')

  try:
    loop = asyncio.get_event_loop()

    # Search query setup for SoundCloud / Multi-platform
    query = (
        f'scsearch1:{search}' if not search.startswith('http') else search
    )

    data = await loop.run_in_executor(
        None, lambda: ytdl.extract_info(query, download=False)
    )

    if 'entries' in data and data['entries']:
      song_info = data['entries'][0]
    else:
      song_info = data

    song_url = song_info.get('url')
    song_title = song_info.get('title', 'Audio Stream')

    if ctx.voice_client.is_playing():
      ctx.voice_client.stop()

    source = discord.FFmpegPCMAudio(song_url, **FFMPEG_OPTIONS)
    ctx.voice_client.play(source)

    await msg.edit(
        content=f'🎶 **Now Playing (SoundCloud / Stream):** `{song_title}`'
    )

  except Exception as e:
    await msg.edit(content=f'⚠️ **Play Error:** `{e}`')


@bot.command(name='leave')
async def leave(ctx):
  if ctx.voice_client:
    await ctx.voice_client.disconnect()
    await ctx.send('👋 **VC से बाहर आ गया!**')


keep_alive()
bot.run(os.environ.get('DISCORD_TOKEN'))

