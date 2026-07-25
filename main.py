import asyncio
import os
from threading import Thread
import urllib.parse
from flask import Flask
import discord
from discord.ext import commands
import requests

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


def search_audio_track(query):
  """SoundCloud HTML / Direct Search API (No YouTube Cookies Needed!)"""
  try:
    encoded_query = urllib.parse.quote(query)

    # SoundCloud Direct Search API
    sc_url = f'https://api-v2.soundcloud.com/search/tracks?q={encoded_query}&client_id=iZ864q22S93f2P1H125O5s089u03s810&limit=1'
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
    }

    res = requests.get(sc_url, headers=headers, timeout=8)

    if res.status_code == 200 and res.json().get('collection'):
      track = res.json()['collection'][0]
      title = track.get('title', 'Audio Stream')

      # Check media streams
      transcodings = track.get('media', {}).get('transcodings', [])
      for trans in transcodings:
        if trans.get('format', {}).get('protocol') == 'progressive':
          stream_info = requests.get(
              f"{trans['url']}?client_id=iZ864q22S93f2P1H125O5s089u03s810",
              headers=headers,
              timeout=5,
          ).json()
          if stream_info.get('url'):
            return stream_info['url'], title

    return None, None
  except Exception as e:
    print(f'Search Error: {e}')
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
      None, lambda: search_audio_track(search)
  )

  if not song_url:
    await msg.edit(
        content=(
            '❌ **ऑडियो ट्रैक नहीं मिल पाया! थोड़ा अलग नाम लिखकर ट्राई करें'
            ' (जैसे: Arijit Singh Lofi / Kesariya)।**'
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
    
