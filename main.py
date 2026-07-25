import asyncio
import os
from threading import Thread
import urllib.parse
from flask import Flask
import discord
from discord.ext import commands
import requests
import yt_dlp

# --- 🌐 Keep Alive Web Server ---
app = Flask('')


@app.route('/')
def home():
  return 'Bot is Alive & Working!'


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

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'nocheckcertificate': True,
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)


def get_stream_url(search_query):
  """Piped API से डायरेक्ट ऑडियो URL ढूँढता है (No YouTube Block Error!)"""
  try:
    if search_query.startswith('http'):
      data = ytdl.extract_info(search_query, download=False)
      return data['url'], data.get('title', 'Audio Track')

    # Search via Piped Engine
    encoded_query = urllib.parse.quote(search_query)
    search_res = requests.get(
        f'https://pipedapi.kavin.rocks/search?q={encoded_query}&filter=music_songs',
        timeout=10,
    ).json()

    if not search_res.get('items'):
      search_res = requests.get(
          f'https://pipedapi.kavin.rocks/search?q={encoded_query}&filter=all',
          timeout=10,
      ).json()

    if not search_res.get('items'):
      return None, None

    video_id = search_res['items'][0]['url'].split('v=')[-1]
    title = search_res['items'][0]['title']

    # Get Stream Info
    stream_data = requests.get(
        f'https://pipedapi.kavin.rocks/streams/{video_id}', timeout=10
    ).json()

    audio_streams = stream_data.get('audioStreams', [])
    if not audio_streams:
      return None, None

    # Best quality audio stream
    audio_url = audio_streams[-1]['url']
    return audio_url, title

  except Exception as e:
    print(f'Search Exception: {e}')
    return None, None


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

  msg = await ctx.send(f'🔍 **Searching Track:** `{search}`...')

  loop = asyncio.get_event_loop()
  song_url, song_title = await loop.run_in_executor(
      None, lambda: get_stream_url(search)
  )

  if not song_url:
    await msg.edit(
        content=(
            '❌ **गाने का लिंक या ऑडियो स्ट्रीम नहीं मिल पाया! थोड़ा अलग नाम'
            ' लिखकर ट्राई करें।**'
        )
    )
    return

  try:
    if ctx.voice_client.is_playing():
      ctx.voice_client.stop()

    source = discord.FFmpegPCMAudio(song_url, **FFMPEG_OPTIONS)
    ctx.voice_client.play(source)

    await msg.edit(content=f'🎶 **Now Playing:** `{song_title}`')

  except Exception as e:
    await msg.edit(content=f'⚠️ **Play Error:** `{e}`')


@bot.command(name='leave')
async def leave(ctx):
  if ctx.voice_client:
    await ctx.voice_client.disconnect()
    await ctx.send('👋 **VC से बाहर आ गया!**')


keep_alive()
bot.run(os.environ.get('DISCORD_TOKEN'))

