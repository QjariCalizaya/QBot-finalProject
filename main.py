import telebot
import os
from telebot import types
from dotenv import load_dotenv
from typing import List, Literal
from db import *

load_dotenv()

TOKEN = os.getenv("TOKEN") or ""

init_db()

bot = telebot.TeleBot(TOKEN)


def setup_bot_commands():
    commands = [
        telebot.types.BotCommand(command='help', description='Здравствуйте. Вы обратились в службу поддержки клиентов. Пожалуйста, введите /start, чтобы начать работу.')


    ]
    bot.set_my_commands(commands)


if __name__ == "__main__":
    setup_bot_commands()
    bot.infinity_polling(skip_pending=True)