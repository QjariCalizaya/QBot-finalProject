import os
import telebot
from telebot import types
from dotenv import load_dotenv
from typing import List, Literal
from db import *
from states import *
from config import *


load_dotenv()

TOKEN = os.getenv("TOKEN") or ""

if not TOKEN:
    raise RuntimeError("there isn't TOKEN in .env")

init_db()
user_states = {}
user_data = {}
ISSUES = {
    "Sin conexión": [
        "Reinicie el router (desconéctelo 30 segundos).",
        "Verifique que el cable WAN esté conectado.",
        "Revise que la luz de Internet esté encendida."
    ],
    "Internet lento": [
        "Reinicie el router.",
        "Desconecte dispositivos que no esté usando.",
        "Conéctese por cable si es posible."
    ],
    "WiFi no aparece": [
        "Verifique que el WiFi esté habilitado.",
        "Reinicie el router.",
        "Acérquese al router."
    ]
}


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

    logger.info(f"/start recibido de user_id={user_id}")

   ####3
    if has_active_appointment(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                text="Cambiar fecha y hora",
                callback_data="change_datetime"
            ),
            types.InlineKeyboardButton(
                text="Cambiar dirección",
                callback_data="change_address"
            )
        )

        bot.send_message(
            user_id,
            "Ya tienes una cita activa.\n¿Qué deseas hacer?",
            reply_markup=markup
        )

        save_user_state(user_id, UserState.CONFIRM.value, {})
        return

 
    state, data = load_user_state(user_id)

#####
    if False: #state
        user_states[user_id] = UserState(state)
        user_data[user_id] = data

        bot.send_message(
            user_id,
            "Continuamos donde lo dejaste."
        )
        return

    #### 
    user_states[user_id] = UserState.START
    user_data[user_id] = {}

    markup = types.InlineKeyboardMarkup()
    for issue in ISSUES.keys():
        print(issue)
        markup.add(
            types.InlineKeyboardButton(
                text=issue,
                callback_data=f"issue:{issue}"
            )

        )


    bot.send_message(
        user_id,
        "👋 Hola, soy el asistente técnico.\nSelecciona el problema que presentas:",
        reply_markup=markup
    )

    save_user_state(user_id, UserState.START.value, {})



@bot.callback_query_handler(func=lambda call: call.data.startswith("issue:"))
def handle_issue(call):
    bot.answer_callback_query(call.id)

    user_id = call.message.chat.id
    issue = call.data.split(":", 1)[1]


    user_states[user_id] = UserState.SHOW_SOLUTIONS
    user_data[user_id]["type"] = issue


    text = "*Soluciones rápidas recomendadas:*\n\n"
    for solution in ISSUES[issue]:
        text += f"• {solution}\n"

    text += "\nSi el problema persiste, puedes solicitar un técnico."

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            text="Solicitar técnico",
            callback_data="request_technician"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            text="🔙 Volver",
            callback_data="back_to_start"
        )
    )

    bot.send_message(
        user_id,
        text,
        reply_markup=markup,
        parse_mode="Markdown"
    )


    save_user_state(
        user_id,
        UserState.SHOW_SOLUTIONS.value,
        user_data[user_id]
    )

@bot.callback_query_handler(func=lambda call: call.data == "back_to_start")
def back_to_start(call):
    bot.answer_callback_query(call.id)


    cmd_start(call.message)


@bot.callback_query_handler(func=lambda call: call.data == "request_technician")
def request_technician(call):
    bot.answer_callback_query(call.id)

    user_id = call.message.chat.id

    if has_active_appointment(user_id):
        bot.send_message(
            user_id,
            " Ya tienes una cita técnica activa.\n"
            "No puedes solicitar otra."
        )
        return

    user_states[user_id] = UserState.NAME
    save_user_state(user_id, UserState.NAME.value, user_data[user_id])

    bot.send_message(
        user_id,
        "Por favor, indica tu *nombre completo*:",
        parse_mode="Markdown"
    )

@bot.message_handler(
    func=lambda message: user_states.get(message.chat.id) == UserState.NAME
)
def handle_client_name(message: types.Message):
    user_id = message.chat.id
    name = message.text.strip()


    if len(name) < 3 or name.isdigit():
        bot.send_message(
            user_id,
            "El nombre ingresado no es válido.\n"
            "Por favor, escribe tu *nombre completo*.",
            parse_mode="Markdown"
        )
        return

    user_data[user_id]["name"] = name
    user_states[user_id] = UserState.ADDRESS

    save_user_state(
        user_id,
        UserState.ADDRESS.value,
        user_data[user_id]
    )

    bot.send_message(
        user_id,
        "Ahora, por favor indica la *dirección completa* donde se realizará la revisión:",
        parse_mode="Markdown"
    )



if __name__ == "__main__":
    setup_bot_commands()
    bot.infinity_polling(skip_pending=True)
    print("bot working")
