import discord
from discord.ext import commands
from discord.utils import get
from datetime import datetime, timedelta
import json
import asyncio

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.reactions = True 
intents.message_content = True  # Ensure the bot can read message content
intents.dm_messages = True  # Ensure the bot can read DMs
intents.dm_reactions = True  # Ensure the bot can handle DM reactions

bot = commands.Bot(command_prefix='!', intents=intents)

with open('env.json') as config_file:
    config = json.load(config_file)

TOKEN = config['TOKEN']
CHANNEL_ID = config['CHANNEL_ID']
MEETINGS_ID = config['MEETINGS_ID']

# Dictionary to keep track of last vent time
last_vent_time = {}
# Dictionary to keep track of user tickets
user_tickets = {}
# Dictionary to keep track of psychologists' availability
psychologists_availability = {}

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')

@bot.event
async def on_message(message):
    if not message.author.bot:
        if isinstance(message.channel, discord.DMChannel):
            if message.content.startswith('!desabafo'):
                await handle_desabafo(message)
            elif message.content.startswith('!marcar'):
                await handle_schedule_meeting(message)
            elif message.content.startswith('!help'):
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
                "Por favor, segue estas regras básicas:\n"
                "1. Sem profanidade.\n"
                "2. Respeita os outros.\n"
                "3. Não compartilhe informações pessoais.\n"
                "4. Ofereça apoio e seja gentil.\n"
                "Obrigado por compartilhares e fazeres parte da comunidade! 💖"
            )
            await thread.send(rules_message)

            await initial_message.add_reaction("⬆️")
            await initial_message.add_reaction("⬇️")
        else:
            await message.author.send("Houve um erro ao enviar a tua mensagem.")

async def handle_schedule_meeting(message):
    user_id = message.author.id
    if user_tickets.get(user_id, 0) < 1:
        await message.author.send("Não tens tickets suficientes para marcar uma reunião. Por favor, pede um ticket a um membro da staff.")
        return

    available_days = [day for day in psychologists_availability]
    if not available_days:
        await message.author.send("Nenhum dia disponível para agendar reuniões.")
        return

    day_message = "Dias disponíveis:\n"
    for i, day in enumerate(available_days):
        day_message += f"{i + 1} - {day.strftime('%d/%m/%Y')}\n"
    day_message += "Por favor, escolha um dia digitando o número correspondente."

    await message.author.send(day_message)

    def check_message_day(m):
        return m.author == message.author and m.content.isdigit() and 1 <= int(m.content) <= len(available_days)

    try:
        day_msg = await bot.wait_for('message', timeout=60.0, check=check_message_day)
        selected_day_index = int(day_msg.content) - 1
        selected_day = available_days[selected_day_index]
    except asyncio.TimeoutError:
        await message.author.send("Tempo esgotado para selecionar um dia.")
        return

    available_times = psychologists_availability[selected_day]
    if not available_times:
        await message.author.send("Nenhuma hora disponível para o dia selecionado.")
        return

    time_message = "Horas disponíveis:\n"
    for i, time in enumerate(available_times):
        time_message += f"{i + 1} - {time}\n"
    time_message += "Por favor, escolhe uma hora digitando o número correspondente."

    await message.author.send(time_message)

    def check_message_time(m):
        return m.author == message.author and m.content.isdigit() and 1 <= int(m.content) <= len(available_times)

    try:
        time_msg = await bot.wait_for('message', timeout=60.0, check=check_message_time)
        selected_time_index = int(time_msg.content) - 1
        selected_time = available_times[selected_time_index]
    except asyncio.TimeoutError:
        await message.author.send("Tempo esgotado para selecionar uma hora.")
        return

    # Remove the selected time from availability
    psychologists_availability[selected_day].remove(selected_time)
    if not psychologists_availability[selected_day]:
        del psychologists_availability[selected_day]

    # Decrement the user's ticket count
    user_tickets[user_id] -= 1

    # Send the meeting details to a specific channel
    schedule_channel = bot.get_channel(MEETINGS_ID)
    await schedule_channel.send(f"Usuário {message.author.name} marcou uma reunião para {selected_day.strftime('%d/%m/%Y')} às {selected_time}.")

    await message.author.send("A tua reunião foi marcada com sucesso.")

@bot.command(name='disponibilidade')
@commands.has_role('Voluntários 🤲')
async def handle_set_availability(ctx):
    await ctx.send("Por favor, envia os dias e horários disponíveis no formato:\n`Dia/Mês - Hora1, Hora2`\nExemplo: `24/08 - 14:00, 15:00`")

    def check_message(m):
        return m.author == ctx.author and m.channel == ctx.channel

    availability_msg = await bot.wait_for('message', check=check_message)
    availability_data = availability_msg.content.split("\n")
    
    for entry in availability_data:
        try:
            date_part, times_part = entry.split(" - ")
            day, month = map(int, date_part.split("/"))
            times_list = [time.strip() for time in times_part.split(",")]

            # Create a datetime object for the day to store availability
            year = datetime.now().year  # Assume current year
            date_str = f"{day:02}/{month:02}/{year:04}"
            date_obj = datetime.strptime(date_str, "%d/%m/%Y").date()

            # Store availability
            if date_obj not in psychologists_availability:
                psychologists_availability[date_obj] = []

            psychologists_availability[date_obj].extend(times_list)
            psychologists_availability[date_obj] = list(set(psychologists_availability[date_obj]))  # Remove duplicates

        except ValueError:
            await ctx.send(f"Formato inválido: {entry}. Por favor, siga o formato `Dia/Mês - Hora1, Hora2`.")

    await ctx.send("Disponibilidade definida com sucesso.")

@bot.command(name='ver_disponibilidade')
@commands.has_role('Voluntários 🤲')
async def handle_view_availability(ctx):
    availability_message = "Disponibilidade dos psicólogos:\n"
    for day, times in psychologists_availability.items():
        availability_message += f"{day.strftime('%d/%m/%Y')}: {', '.join(times)}\n"
    await ctx.send(availability_message)

@bot.command(name='tickets')
@commands.has_role('Staff')
async def handle_view_tickets(ctx):
    tickets_message = "Tickets dos usuários:\n"
    for user_id, tickets in user_tickets.items():
        user = ctx.guild.get_member(user_id)
        if user:
            tickets_message += f"{user.name}: {tickets}\n"
    await ctx.send(tickets_message)

@bot.command(name='help')
async def handle_help(ctx):
    await ctx.send(
        "Comandos disponíveis (apenas por mensagem privada):\n"
        "1. `!desabafo` - Enviar um desabafo anónimo.\n"
        "2. `!marcar` - Marcar uma reunião com um psicólogo.\n")

@bot.command()
@commands.has_role('Staff')
async def add_ticket(ctx, member: discord.Member):
    if member.id not in user_tickets:
        user_tickets[member.id] = 1
    else:
        user_tickets[member.id] += 1
    await ctx.send(f"O usuário {member.name} agora tem {user_tickets[member.id]} tickets.")

bot.run(TOKEN)
