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


def search_jiosaavn(query):
  """JioSaavn API से direct MP3 link ढूँढता है (No YouTube, No Block Error!)"""
  try:
    encoded_query = urllib.parse.quote(query)
    # Fast JioSaavn API Search
    url = f'https://saavn.dev/api/search/songs?query={encoded_query}&limit=1'
    res = requests.get(url, timeout=10).json()

    if res.get('success') and res['data']['results']:
      song = res['data']['results'][0]
      title = (
          f"{song['name']} - {song['artists']['primary'][0]['name']}"
          if song.get('artists')
          else song['name']
      )

      # Highest Quality Audio Stream URL
      download_urls = song.get('downloadUrl', [])
      if download_urls:
        audio_url = download_urls[-1][
            'url'
        ]  # 320kbps or highest quality available
        return audio_url, title

    return None, None
  except Exception as e:
    print(f'JioSaavn Search Error: {e}')
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

  msg = await ctx.send(f'🔍 **Searching Music:** `{search}`...')

  loop = asyncio.get_event_loop()
  song_url, song_title = await loop.run_in_executor(
      None, lambda: search_jiosaavn(search)
  )

  if not song_url:
    await msg.edit(
        content=(
            '❌ **गाने का ऑडियो नहीं मिल पाया! थोड़ा स्पेलिंग चेक करके दोबारा'
            ' कोशिश करें।**'
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
