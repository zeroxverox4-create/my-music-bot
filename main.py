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
  return 'Bot is Alive & Working perfectly!'


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

# Reliable Invidious / Alternative Instances
INVIDIOUS_INSTANCES = [
    'https://invidious.nerdvpn.de',
    'https://inv.tux.pizza',
    'https://invidious.drgns.space',
    'https://vid.puffyan.us',
]


def fetch_audio_stream(query):
  """Multiple Invidious Mirrors से Audio Stream ढूँढता है (No Bot Block Error!)"""
  encoded_query = urllib.parse.quote(query)

  for instance in INVIDIOUS_INSTANCES:
    try:
      # Search video
      search_url = f'{instance}/api/v1/search?q={encoded_query}&type=video'
      res = requests.get(search_url, timeout=5)

      if res.status_code == 200 and res.json():
        items = res.json()
        if not items:
          continue

        video_id = items[0]['videoId']
        title = items[0]['title']

        # Fetch video stream details
        video_url = f'{instance}/api/v1/videos/{video_id}'
        video_res = requests.get(video_url, timeout=5)

        if video_res.status_code == 200:
          data = video_res.json()
          adaptive_formats = data.get('adaptiveFormats', [])

          # Pick best audio stream
          audio_streams = [
              f
              for f in adaptive_formats
              if f.get('type', '').startswith('audio/')
          ]
          if audio_streams:
            # Sort by highest bitrate
            audio_streams.sort(
                key=lambda x: int(x.get('bitrate', 0)), reverse=True
            )
            return audio_streams[0]['url'], title
    except Exception as e:
      print(f'Failed on instance {instance}: {e}')
      continue

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
      None, lambda: fetch_audio_stream(search)
  )

  if not song_url:
    await msg.edit(
        content=(
            '❌ **ऑडियो नहीं मिल पाया! थोड़ा अलग नाम लिखकर प्रयास करें।**'
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

