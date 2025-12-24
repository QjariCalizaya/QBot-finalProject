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
        


    ]
    bot.set_my_commands(commands)