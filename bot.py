import discord
from discord.ext import commands
from discord.utils import get
from datetime import datetime, timedelta
import json

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.reactions = True 
intents.message_content = True  # Ensure the bot can read message content

bot = commands.Bot(command_prefix='!', intents=intents)

with open('env.json') as config_file:
    config = json.load(config_file)

TOKEN = config['TOKEN']
CHANNEL_ID = config['CHANNEL_ID']

# Dictionary to keep track of last vent time
last_vent_time = {}
# Dictionary to keep track of user tickets
user_tickets = {}
# Dictionary to keep track of psychologists' availability
psychologists_availability = {}

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_message(message):
    if not message.author.bot:
        if isinstance(message.channel, discord.DMChannel):
            if message.content.startswith('!desabafo'):
                await handle_desabafo(message)
            elif message.content.startswith('!marcar'):
                await handle_schedule_meeting(message)
            else:
                await message.author.send(
                    "Comandos disponíveis:\n"
                    "1. `!desabafo` - Enviar um desabafo anónimo.\n"
                    "2. `!marcar` - Marcar uma reunião com um psicólogo.\n"
                )
    await bot.process_commands(message)


async def handle_desabafo(message):
    user_id = message.author.id
    current_time = datetime.now()

    if user_id in last_vent_time and (current_time - last_vent_time[user_id]) < timedelta(days=1):
        time_to_send = last_vent_time[user_id] + timedelta(days=1) + timedelta(hours=1)
        time_to_send = time_to_send.strftime("%d/%m/%Y %H:%M:%S")
        await message.author.send("Só é possível enviar um desabafo por dia. Podes enviar outro: " + time_to_send)
    else:
        last_vent_time[user_id] = current_time
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            initial_message = await channel.send(f'Desabafo diário: {message.content[len("!desabafo"):].strip()}')
            thread = await channel.create_thread(
                name=f"Desabafo anónimo",
                type=discord.ChannelType.public_thread,
                message=initial_message
            )
            await message.author.send("O teu desabafo foi enviado anonimamente.")

            rules_message = (
                "Bem-vindo ao tópico de desabafo! 🌟\n"
                "Por favor, siga estas regras básicas:\n"
                "1. Sem profanidade.\n"
                "2. Respeite os outros.\n"
                "3. Não compartilhe informações pessoais.\n"
                "4. Ofereça apoio e seja gentil.\n"
                "Obrigado por compartilhar e fazer parte da comunidade! 💖"
            )
            await thread.send(rules_message)

            await initial_message.add_reaction("⬆️")
            await initial_message.add_reaction("⬇️")
        else:
            await message.author.send("Houve um erro ao enviar sua mensagem.")

async def handle_schedule_meeting(message):
    user_id = message.author.id
    if user_tickets.get(user_id, 0) < 1:
        await message.author.send("Você não tem tickets suficientes para marcar uma reunião. Por favor, peça um ticket a um membro da staff.")
        return
    
    available_days = [day for day in psychologists_availability]
    if not available_days:
        await message.author.send("Nenhum dia disponível para agendar reuniões.")
        return
    
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣"]
    day_message = "Dias disponíveis:\n"
    for i, day in enumerate(available_days):
        day_message += f"{emojis[i]} - {day}\n"
    day_message += "Por favor, escolha um dia reagindo com o emoji correspondente."
    
    day_msg = await message.author.send(day_message)
    for emoji in emojis[:len(available_days)]:
        await day_msg.add_reaction(emoji)
    
    def check(reaction, user):
        return user == message.author and str(reaction.emoji) in emojis
    
    reaction, user = await bot.wait_for('reaction_add', check=check)
    selected_day = available_days[emojis.index(str(reaction.emoji))]
    
    available_times = psychologists_availability[selected_day]
    time_message = "Horas disponíveis:\n"
    for time in available_times:
        time_message += f"{time}\n"
    time_message += "Por favor, escolha uma hora respondendo com a hora desejada."
    
    await message.author.send(time_message)
    
    def check_message(m):
        return m.author == message.author and m.content in available_times
    
    time_msg = await bot.wait_for('message', check=check_message)
    selected_time = time_msg.content
    
    # Remove the selected time from availability
    psychologists_availability[selected_day].remove(selected_time)
    if not psychologists_availability[selected_day]:
        del psychologists_availability[selected_day]
    
    # Decrement the user's ticket count
    user_tickets[user_id] -= 1
    
    # Send the meeting details to a specific channel
    schedule_channel = bot.get_channel(CHANNEL_ID)
    await schedule_channel.send(f"Usuário {message.author.name} marcou uma reunião para {selected_day} às {selected_time}.")
    
    await message.author.send("Sua reunião foi marcada com sucesso.")

@bot.command(name='disponibilidade')
@commands.has_role('Voluntários 🤲')
async def handle_set_availability(ctx):
    if isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("Este comando só pode ser usado em um servidor.")
        return

    await ctx.send("Por favor, envie os dias e horários disponíveis no formato:\nDia1: Hora1, Hora2\nDia2: Hora3, Hora4")

    def check_message(m):
        return m.author == ctx.author and m.channel == ctx.channel

    availability_msg = await bot.wait_for('message', check=check_message)
    availability_data = availability_msg.content.split("\n")
    for entry in availability_data:
        day, times = entry.split(":")
        times_list = [time.strip() for time in times.split(",")]
        psychologists_availability[day.strip()] = times_list

    await ctx.send("Disponibilidade definida com sucesso.") 

@bot.command()
@commands.has_role('Staff')
async def add_ticket(ctx, member: discord.Member):
    if member.id not in user_tickets:
        user_tickets[member.id] = 1
    else:
        user_tickets[member.id] += 1
    await ctx.send(f"O usuário {member.name} agora tem {user_tickets[member.id]} tickets.")



bot.run(TOKEN)
