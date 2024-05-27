import discord
from discord.ext import commands
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

TOKEN = OCULTO
CHANNEL_ID = OCULTO

# Dictionary to keep track of last vent time
last_vent_time = {}

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')

@bot.event
async def on_message(message):
    if isinstance(message.channel, discord.DMChannel) and not message.author.bot:
        user_id = message.author.id
        current_time = datetime.now()

        if message.content.startswith('!desabafo'):
            if user_id in last_vent_time and (current_time - last_vent_time[user_id]) < timedelta(days=1):
                await message.author.send("Só é possível enviar um desabafo por dia. Por favor, tenta novamente amanhã.")
            else:
                last_vent_time[user_id] = current_time
                channel = bot.get_channel(CHANNEL_ID)
                if channel:
                    await channel.send(f'Desabafo diário: {message.content[len("!desabafo"):].strip()}')
                    await message.author.send("Seu desabafo foi enviado anonimamente.")
                else:
                    await message.author.send("Houve um erro ao enviar sua mensagem.")
        else:
            await message.author.send(
                "Para enviar um desabafo, começa a tua mensagem com ***!desabafo***.\n"
                "Só podes enviar **um desabafo por dia**, então pensa bem em como estruturar a tua mensagem.\n"
                "Se possível, identifica-te mencionando o teu género e idade (se não estiveres confortável com a idade exata, coloca uma idade aproximada).\n"
                "*Exemplo:* !desabafo Eu, (M 23), tenho passado por uma fase difícil no trabalho..."
            )
    await bot.process_commands(message)

bot.run(TOKEN)
