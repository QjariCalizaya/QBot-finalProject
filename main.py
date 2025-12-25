import os
import telebot
from telebot import types
from dotenv import load_dotenv
from typing import List, Literal
from db import *
import logging

load_dotenv()

TOKEN = os.getenv("TOKEN") or ""

if not TOKEN:
    raise RuntimeError("there isn't TOKEN in .env")

init_db()

bot = telebot.TeleBot(TOKEN)


def setup_bot_commands():
    commands = [
        telebot.types.BotCommand(command='help', description='справка и доступные функции'),
        telebot.types.BotCommand(command="start", description="начать работу с ботом")

    ]
    bot.set_my_commands(commands)




@bot.message_handler(commands=['help'])
def cmd_help(message:types.Message)-> None:
    text= (
"""Доступные команды:

/start — начать работу с ботом
/help — показать справку"""
    )
    bot.send_message(message.chat.id,text=text)


@bot.message_handler(commands=["start"])
def cmd_start(message):
    user_id = message.chat.id

    #logger.info(f"/start recibido de user_id={user_id}")

    if has_active_appointment(user_id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Cambiar fecha y hora", "Cambiar dirección")

        bot.send_message(
            user_id,
            "📅 Ya tienes una cita técnica activa.\n"
            "¿Qué deseas hacer?",
            reply_markup=markup
        )

        save_user_state(user_id, UserState.CONFIRM.name, {})
        return

    state, data = load_user_state(user_id)

    if state:
        user_states[user_id] = UserState[state]
        user_data[user_id] = data

        bot.send_message(
            user_id,
            "🔄 Bienvenido de nuevo.\n"
            "Continuamos donde lo dejaste."
        )

        logger.info(
            f"Estado restaurado para user_id={user_id}: {state}"
        )
        return

    # 3️⃣ Inicio normal del flujo
    user_states[user_id] = UserState.START
    user_data[user_id] = {}

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for issue in ISSUES.keys():
        markup.add(issue)

    bot.send_message(
        user_id,
        "👋 Hola, soy el asistente técnico del servicio de internet.\n\n"
        "Selecciona el problema que estás presentando:",
        reply_markup=markup
    )

    # Persistimos estado inicial
    save_user_state(user_id, UserState.START.name, {})

    logger.info(f"Flujo iniciado para user_id={user_id}")


if __name__ == "__main__":
    setup_bot_commands()
    bot.infinity_polling(skip_pending=True)
    print("bot working")
