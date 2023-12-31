import discord
from discord.ext import commands
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote
import json
import time
import asyncio

with open('config.json') as f:
    config = json.load(f)

DISCORD_TOKEN = config.get('discord_token')
SHAREUS_API_KEY = config.get('shareus_api_key')
WEBSITE_URL = config.get('website_url', 'https://example.com/apks')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

setup_channels = {}
downloaded_apks = set()

try:
    with open('downloaded_apks.txt', 'r') as log_file:
        downloaded_apks.update(line.strip() for line in log_file)
except FileNotFoundError:
    pass

def shorten_url(original_url):
    shortener_url = f'https://api.shareus.io/easy_api?key={SHAREUS_API_KEY}&link={original_url}'
    response = requests.get(shortener_url)

    if response.status_code == 200:
        return response.text.strip()
    else:
        return f'Error: {response.text}'

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="VisualELF"))
    print(f'Logged in as {bot.user.name} ({bot.user.id})')

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx, channel_id: int):
    guild_id = ctx.guild.id

    if guild_id not in setup_channels:
        setup_channels[guild_id] = {}

    if channel_id in setup_channels[guild_id].values():
        await ctx.send("Channel already set up.")
    else:
        setup_channels[guild_id]['channel_id'] = channel_id
        await ctx.send(f"Channel set up successfully. Mod APK links will be sent to channel ID {channel_id} on this server.")

@bot.command()
@commands.has_permissions(administrator=True)
async def start(ctx):
    guild_id = ctx.guild.id

    if guild_id not in setup_channels or 'channel_id' not in setup_channels[guild_id]:
        await ctx.send("Please run `!setup {channel_id}` to set up the channel first.")
        return

    channel_id = setup_channels[guild_id]['channel_id']
    channel = bot.get_channel(channel_id)

    if not channel:
        await ctx.send(f"Invalid channel. Please run `!setup {channel_id}` again.")
        return

    try:
        response = requests.get(WEBSITE_URL)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        apk_links = soup.find_all('a', href=lambda href: (href and href.endswith('.apk')))

        for link in apk_links:
            file_url = urljoin(WEBSITE_URL, link['href'])
            file_name = link['href'].split('/')[-1]

            if file_name in downloaded_apks:
                print(f"Skipping already processed APK: {file_name}")
                continue

            try:
                apk_response = requests.get(file_url)
                apk_response.raise_for_status()

                shortened_url = shorten_url(file_url)

                embed = discord.Embed(title=f"Mod APK: {unquote(file_name)}", 
                description=f"Size: {len(apk_response.content) / (1024 * 1024):.2f} MB\n ━━━━━━━━━━━━━━━━━ \n Features: \n・ Min-Engine: Android 5.0 \n  ・ Sudo: Non-Root \n  ・ Architecture: 32bit/64bit \n  ・ Minimum Ram: 2gb", color=discord.Color.green())

                embed.add_field(name="Download", value=shortened_url, inline=False)
                thumbnail_url = "https://cdn.discordapp.com/attachments/1153874384289812551/1190968857393901630/communityIcon_q69d9lxagoi31.png?ex=65a3bb2e&is=6591462e&hm=0aace23c5be3eec2ce5a6681230a61fcbc05c1676da15f1f84c1d683e5003dc1&"
                main_image_url = "https://cdn.discordapp.com/attachments/1153874384289812551/1190970979032240148/20231231_162303.jpg?ex=65a3bd28&is=65914828&hm=13061a28841ab28b9edff2e5a8c6d0f26b05eb7a3f7c3947bf337d00b6597151&"
                footer_image_url = "https://cdn.discordapp.com/attachments/1153874384289812551/1190971025773559868/3937bafd4789a107b6a245ab983ea297.png?ex=65a3bd33&is=65914833&hm=0deff3b35f562e6fae8bb710230cd867344ab8edf198cabf686ebd16d9902585&"

                embed.set_thumbnail(url=thumbnail_url)
                embed.set_image(url=main_image_url)

                footer_text = f"Date uploaded: {time.strftime('%Y.%m.%d・%H:%M:%S')}"
                embed.set_footer(text=footer_text, icon_url=footer_image_url)

                await channel.send(embed=embed)
                await asyncio.sleep(3)

                downloaded_apks.add(file_name)
                with open('downloaded_apks.txt', 'a') as log_file:
                    log_file.write(f"{file_name}\n")

            except requests.RequestException as e:
                embed = discord.Embed(title="Error",
                                      description=f"An error occurred: {e}",
                                      color=discord.Color.red())
                await channel.send(embed=embed)
                print(f'Error during APK file processing: {e}')

    except requests.RequestException as e:
        embed = discord.Embed(title="Error",
                              description=f"An error occurred: {e}",
                              color=discord.Color.red())
        await channel.send(embed=embed)
        print(f'Error accessing the website. Status code: {e}')

@start.error
async def start_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have the required permissions to use this command.")
    else:
        await ctx.send(f"An error occurred: {error}")

bot.run(DISCORD_TOKEN)
