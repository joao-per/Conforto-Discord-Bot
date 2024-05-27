import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

TOKEN = 'YOUR_BOT_TOKEN'
CHANNEL_ID = YOUR_CHANNEL_ID

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')

@bot.event
async def on_message(message):
    if isinstance(message.channel, discord.DMChannel) and not message.author.bot:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(f'Anonymous user says: {message.content}')
            await message.author.send("Your message has been sent anonymously.")
        else:
            await message.author.send("There was an error sending your message.")
    await bot.process_commands(message)

bot.run(TOKEN)
