import discord
from discord.ext import commands
from discord.utils import get
from datetime import datetime, timedelta
import json
import asyncio
import mysql.connector
from mysql.connector import errorcode
from db_config import db_config

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.reactions = True 
intents.message_content = True
intents.dm_messages = True
intents.dm_reactions = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

with open('env.json') as config_file:
    config = json.load(config_file)

TOKEN = config['TOKEN']
CHANNEL_ID = config['CHANNEL_ID']
MEETINGS_ID = config['MEETINGS_ID']

cnx = None
cursor = None

# Database connection
try:
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Something is wrong with the user name or password")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("Database does not exist")
    else:
        print(err)

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')

@bot.event
async def on_member_join(member):
    welcome_channel = bot.get_channel(CHANNEL_ID)
    if welcome_channel:
        await welcome_channel.send(
            f"Bem-vindo(a) ao servidor, {member.mention}! Aqui estão os comandos disponíveis:\n"
            "1. `!desabafo` - Enviar um desabafo anónimo.\n"
            "2. `!marcar` - Marcar uma reunião com um psicólogo.\n"
            "3. `!disponibilidade` - Definir disponibilidade (apenas para psicólogos).\n"
            "4. `!add_ticket` - Adicionar um ticket para um usuário (apenas para staff).\n"
            "5. `!help` - Exibir esta mensagem de ajuda novamente."
        )

@bot.event
async def on_message(message):
    if not message.author.bot:
        if isinstance(message.channel, discord.DMChannel):
            if message.content.startswith('!desabafo'):
                if len(message.content.strip()) == len('!desabafo'):
                    await message.author.send(
                        "Para usar o comando `!desabafo`, envie `!desabafo` seguido do seu desabafo.\n"
                        "Exemplo: `!desabafo Estou me sentindo triste hoje.`"
                    )
                else:
                    await handle_desabafo(message)
            elif message.content.startswith('!marcar'):
                await handle_schedule_meeting(message)

    await bot.process_commands(message)

async def handle_desabafo(message):
    user_id = message.author.id
    current_time = datetime.now()

    cursor.execute("SELECT last_vent_time FROM user_tickets WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()

    if result and (current_time - result[0]) < timedelta(days=1):
        time_to_send = result[0] + timedelta(days=1) + timedelta(hours=1)
        time_to_send = time_to_send.strftime("%d/%m/%Y %H:%M:%S")
        await message.author.send(f"Só é possível enviar um desabafo por dia. Podes enviar outro: {time_to_send}")
    else:
        cursor.execute(
            "INSERT INTO user_tickets (user_id, last_vent_time) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE last_vent_time = VALUES(last_vent_time)",
            (user_id, current_time)
        )
        cnx.commit()

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
    cursor.execute("SELECT tickets FROM user_tickets WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    tickets = result[0] if result else 0

    if tickets < 1:
        await message.author.send("Você não tem tickets suficientes para marcar uma reunião. Por favor, peça um ticket a um membro da staff.")
        return

    cursor.execute("SELECT DISTINCT date FROM psychologist_availability ORDER BY date")
    available_days = cursor.fetchall()
    if not available_days:
        await message.author.send("Nenhum dia disponível para agendar reuniões.")
        return

    day_message = "Dias disponíveis:\n"
    for i, (day,) in enumerate(available_days):
        day_message += f"{i + 1} - {day.strftime('%d/%m/%Y')}\n"
    day_message += "Por favor, escolha um dia digitando o número correspondente."

    await message.author.send(day_message)

    def check_message_day(m):
        return m.author == message.author and m.content.isdigit() and 1 <= int(m.content) <= len(available_days)

    try:
        day_msg = await bot.wait_for('message', timeout=60.0, check=check_message_day)
        selected_day_index = int(day_msg.content) - 1
        selected_day = available_days[selected_day_index][0]
    except asyncio.TimeoutError:
        await message.author.send("Tempo esgotado para selecionar um dia.")
        return

    cursor.execute(
        "SELECT time, psychologist_name FROM psychologist_availability WHERE date = %s ORDER BY time",
        (selected_day,)
    )
    available_times = cursor.fetchall()
    if not available_times:
        await message.author.send("Nenhuma hora disponível para o dia selecionado.")
        return

    time_message = "Horas disponíveis:\n"
    for i, (time, _) in enumerate(available_times):
        time_message += f"{i + 1} - {time}\n"
    time_message += "Por favor, escolha uma hora digitando o número correspondente."

    await message.author.send(time_message)

    def check_message_time(m):
        return m.author == message.author and m.content.isdigit() and 1 <= int(m.content) <= len(available_times)

    try:
        time_msg = await bot.wait_for('message', timeout=60.0, check=check_message_time)
        selected_time_index = int(time_msg.content) - 1
        selected_time, selected_psychologist = available_times[selected_time_index]
    except asyncio.TimeoutError:
        await message.author.send("Tempo esgotado para selecionar uma hora.")
        return

    cursor.execute(
        "DELETE FROM psychologist_availability WHERE date = %s AND time = %s",
        (selected_day, selected_time)
    )
    cnx.commit()

    cursor.execute(
        "UPDATE user_tickets SET tickets = tickets - 1 WHERE user_id = %s",
        (user_id,)
    )
    cnx.commit()

    schedule_channel = bot.get_channel(MEETINGS_ID)
    await schedule_channel.send(
        f"Usuário {message.author.name} marcou uma reunião com {selected_psychologist} para {selected_day.strftime('%d/%m/%Y')} às {selected_time}."
    )

    await message.author.send("Sua reunião foi marcada com sucesso.")

@bot.command(name='disponibilidade')
@commands.has_role('Voluntários 🤲')
async def handle_set_availability(ctx):
    await ctx.send("Por favor, envie os dias e horários disponíveis no formato:\n`Dia/Mês - Hora1, Hora2`\nExemplo: `24/08 - 14:00, 15:00`")

    def check_message(m):
        return m.author == ctx.author and m.channel == ctx.channel

    availability_msg = await bot.wait_for('message', check=check_message)
    availability_data = availability_msg.content.split("\n")

    for entry in availability_data:
        try:
            date_part, times_part = entry.split(" - ")
            day, month = map(int, date_part.split("/"))
            times_list = [time.strip() for time in times_part.split(",")]

            year = datetime.now().year
            date_str = f"{day:02}/{month:02}/{year:04}"
            date_obj = datetime.strptime(date_str, "%d/%m/%Y").date()

            for time in times_list:
                cursor.execute(
                    "INSERT INTO psychologist_availability (date, time, psychologist_name) VALUES (%s, %s, %s)",
                    (date_obj, time, ctx.author.name)
                )
            cnx.commit()
        except ValueError:
            await ctx.send(f"Formato inválido: {entry}. Por favor, siga o formato `Dia/Mês - Hora1, Hora2`.")

    await ctx.send("Disponibilidade definida com sucesso.")

@bot.command(name='ver_disponibilidade')
@commands.has_role('Voluntários 🤲')
async def handle_view_availability(ctx):
    cursor.execute("SELECT date, time, psychologist_name FROM psychologist_availability ORDER BY date, time")
    results = cursor.fetchall()
    availability_message = "Disponibilidade dos psicólogos:\n"
    for date, time, psychologist in results:
        availability_message += f"{date.strftime('%d/%m/%Y')} {time} - {psychologist}\n"
    await ctx.send(availability_message)

@bot.command(name='tickets')
@commands.has_role('Staff')
async def handle_view_tickets(ctx):
    cursor.execute("SELECT user_id, tickets FROM user_tickets")
    results = cursor.fetchall()
    tickets_message = "Tickets dos usuários:\n"
    for user_id, tickets in results:
        user = ctx.guild.get_member(user_id)
        if user:
            tickets_message += f"{user.name}: {tickets}\n"
    await ctx.send(tickets_message)

# do bot command to be !help and !ajuda
@bot.command(name='help')
async def custom_help(ctx):
    await ctx.send(
        "Comandos disponíveis:\n"
        "1. `!desabafo` - Enviar um desabafo anónimo.\n"
        "2. `!marcar` - Marcar uma reunião com um psicólogo.\n"
        "3. `!help` - Exibir esta mensagem de ajuda.\n"
        "4. `!disponibilidade` - Definir disponibilidade (apenas para psicólogos).\n"
        "5. `!add_ticket` - Adicionar um ticket para um usuário (apenas para staff).\n"
        "6. `!tickets` - Ver tickets dos usuários (apenas para staff).\n"
        "7. `!ver_disponibilidade` - Ver disponibilidade dos psicólogos (apenas para psicólogos).\n"
        "8. `!ajuda` - Exibir esta mensagem de ajuda novamente."
    )

@bot.command()
@commands.has_role('Staff')
async def add_ticket(ctx, member: discord.Member):
    cursor.execute("SELECT tickets FROM user_tickets WHERE user_id = %s", (member.id,))
    result = cursor.fetchone()
    if result:
        cursor.execute("UPDATE user_tickets SET tickets = tickets + 1 WHERE user_id = %s", (member.id,))
    else:
        cursor.execute("INSERT INTO user_tickets (user_id, tickets) VALUES (%s, %s)", (member.id, 1))
    cnx.commit()
    await ctx.send(f"O usuário {member.name} agora tem {result[0] + 1 if result else 1} tickets.")

bot.run(TOKEN)

# Close the database connection when the bot stops
@bot.event
async def on_disconnect():
    cursor.close()
    cnx.close()
