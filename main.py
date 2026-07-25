import asyncio
import os
from threading import Thread

import discord
from discord.ext import commands
from flask import Flask
import yt_dlp

# --- 🌐 Keep Alive Web Server ---
app = Flask('')


@app.route('/')
def home():
  return 'Bot is alive and YouTube-Blocked!'


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

# --- 🎵 STRICT Non-YouTube Engine ---
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'scsearch10:',  # 🔥 Fix: 10 रिजल्ट में से बेस्ट गाने पकड़ेगा
    'nocheckcertificate': True,
    'allowed_extractors': [
        'soundcloud',
        'soundcloud:search',
        'generic',
        'bandcamp',
        'vimeo',
        'twitch',
    ],
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)


@bot.event
async def on_ready():
  print(f'✅ Bot Active: {bot.user.name}')


@bot.command(name='play')
async def play(ctx, *, search: str):
  if not ctx.author.voice:
    await ctx.send('❌ **भाई, पहले किसी Voice Channel (VC) में जुड़ो!**')
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

  msg = await ctx.send(f'🔍 **Searching SoundCloud:** `{search}`...')

  try:
    loop = asyncio.get_event_loop()

    # Always force SoundCloud search with results
    if not search.startswith('http'):
      query = f'scsearch10:{search}'
    else:
      query = search

    data = await loop.run_in_executor(
        None, lambda: ytdl.extract_info(query, download=False)
    )

    if not data:
      await msg.edit(
          content=(
              '❌ **SoundCloud पर यह गाना नहीं मिला। थोड़ा अलग नाम लिखकर ट्राई'
              ' करें!**'
          )
      )
      return

    if 'entries' in data and data['entries']:
      # फ़िल्टर करके पहला वैलिड गाना उठाएगा
      song_info = None
      for entry in data['entries']:
        if entry:
          song_info = entry
          break

      if not song_info:
        await msg.edit(content='❌ **कोई सही ऑडियो ट्रैक नहीं मिला!**')
        return
    else:
      song_info = data

    song_url = song_info.get('url')
    song_title = song_info.get('title', 'Audio Stream')

    if ctx.voice_client.is_playing():
      ctx.voice_client.stop()

    source = discord.FFmpegPCMAudio(song_url, **FFMPEG_OPTIONS)
    ctx.voice_client.play(source)

    await msg.edit(content=f'🎶 **Now Playing (SoundCloud):** `{song_title}`')

  except Exception as e:
    await msg.edit(
        content=(
            '⚠️ **Play Error:** SoundCloud पर यह गाना ढूंढने में दिक्कत आई।'
        )
    )


@bot.command(name='leave')
async def leave(ctx):
  if ctx.voice_client:
    await ctx.voice_client.disconnect()
    await ctx.send('👋 **VC से बाहर आ गया!**')


keep_alive()
bot.run(os.environ.get('DISCORD_TOKEN'))
    
