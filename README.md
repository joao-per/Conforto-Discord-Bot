# 🛠️ Discord Vent Bot

Welcome to the Discord Vent Bot! This bot is designed to create a safe and anonymous space for users to vent their feelings and seek support in your Discord server. 🌈

## 🤖 Bot Functionality

The Vent Bot has the following features:

1. **Anonymous Venting**: Users can send a direct message to the bot starting with `!desabafo`. The bot will post the message anonymously in a designated channel.
2. **Daily Limit**: Each user can send one vent message per day to ensure thoughtful communication.
3. **Guidance Message**: If a user sends a message without the `!desabafo` keyword, the bot will respond with instructions on how to use the bot (in Portuguese).

## 🚀 Getting Started

To get your Vent Bot up and running, follow these steps:

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/discord-vent-bot.git
cd discord-vent-bot
```

### 2. Install Dependencies
Ensure you have Python installed, then install the required libraries:

```bash
pip install -r requirements.txt
```

### 3. Create the Configuration File
You need to create a config.json file in the root directory of the project. This file should contain your bot token and the ID of the channel where the vent messages will be posted.

```json
{
    "TOKEN": "YOUR_BOT_TOKEN",
    "CHANNEL_ID": YOUR_CHANNEL_ID
}
```

### 4. Run the Bot
Start the bot using the following command:

```bash
python bot.py
```

## 📚 How to Use
1. Start Your Message: Begin your message with !desabafo.
2. Include Important Details: Mention your gender and age (approximate age if you're not comfortable with the exact number).
3. Send the Message: The bot will post your message anonymously in the designated channel.

## 🛠️ Contribution
Feel free to fork this repository and submit pull requests. For major changes, please open an issue first to discuss what you would like to change.

## 📧 Support
If you have any questions or need help, feel free to open an issue or contact me directly.

**Happy venting!** 💬✨