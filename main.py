import os
import telebot
from telebot import types
from dotenv import load_dotenv
from typing import List, Literal
from db import *
from states import *
from config import *
from datetime import date, timedelta


load_dotenv()

TOKEN = os.getenv("TOKEN") or ""
WORKING_HOURS = list(range(9, 18))

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
        telebot.types.BotCommand(command="start", description="начать работу с ботом"),
        telebot.types.BotCommand(command="change", description="изменить время приема"),
        

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
            text="Volver",
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
    user_states[user_id] = UserState.PHONE
    save_user_state(user_id, UserState.PHONE.value, user_data[user_id])

    bot.send_message(
        user_id,
        "Por favor, indica tu *número de contacto*:\n"
        "Ejemplo: +34123456789",
        parse_mode="Markdown"
    )

@bot.message_handler(
    func=lambda message: user_states.get(message.chat.id) == UserState.PHONE
)
def handle_client_phone(message: types.Message):
    user_id = message.chat.id
    phone = message.text.strip()

    if len(phone) < 7 or not any(char.isdigit() for char in phone):
        bot.send_message(
            user_id,
            "El número ingresado no es válido.\n"
            "Por favor, escribe un *número de contacto válido*.",
            parse_mode="Markdown"
        )
        return

    user_data[user_id]["phone"] = phone

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





@bot.message_handler(
    func=lambda message: user_states.get(message.chat.id) == UserState.ADDRESS
)
def handle_client_address(message: types.Message):
    user_id = message.chat.id
    address = message.text.strip()

    if len(address) < 5 or address.isdigit():
        bot.send_message(
            user_id,
            "La dirección ingresada no es válida.\n"
            "Por favor, escribe una *dirección completa* (calle, número, referencia).",
            parse_mode="Markdown"
        )
        return

    user_data[user_id]["address"] = address
    user_states[user_id] = UserState.DATE

    save_user_state(
        user_id,
        UserState.DATE.value,
        user_data[user_id]
    )

    bot.send_message(
        user_id,
        "Dirección guardada correctamente.\n"
        "A continuación podrás seleccionar la *fecha de la cita*."
    )
    show_date_selection(user_id)


def get_next_7_days():
    today = date.today()
    days = []
    for i in range(1, 8):
        d = today + timedelta(days=i)
        days.append(d)
    return days

def show_date_selection(user_id):
    markup = types.InlineKeyboardMarkup()

    for d in get_next_7_days():
        label = d.strftime("%A %d-%m")
        callback = f"date:{d.isoformat()}"

        markup.add(
            types.InlineKeyboardButton(
                text=label,
                callback_data=callback
            )
        )

    markup.add(
        types.InlineKeyboardButton(
            text="Volver",
            callback_data="back_to_start"
        )
    )

    bot.send_message(
        user_id,
        "Selecciona la *fecha* para la visita técnica:",
        reply_markup=markup,
        parse_mode="Markdown"
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("date:"))
def handle_date_selection(call):
    bot.answer_callback_query(call.id)

    user_id = call.message.chat.id
    date_selected = call.data.split(":", 1)[1]

 
    user_data[user_id]["date"] = date_selected


    user_states[user_id] = UserState.HOUR

    save_user_state(
        user_id,
        UserState.HOUR.value,
        user_data[user_id]
    )

    bot.send_message(
        user_id,
        f"Fecha seleccionada: *{date_selected}*\n"
        "Ahora selecciona el *horario disponible*.",
        parse_mode="Markdown"
    )

    show_hour_selection(user_id)


def show_hour_selection(user_id):
    selected_date = user_data[user_id]["date"]

    taken_hours = get_taken_hours(selected_date)
    available_hours = [
        h for h in WORKING_HOURS if h not in taken_hours
    ]

    if not available_hours:
        bot.send_message(
            user_id,
            "No hay horarios disponibles para esta fecha.\n"
            "Por favor selecciona otra fecha."
        )
        show_date_selection(user_id)
        return

    markup = types.InlineKeyboardMarkup()

    for hour in available_hours:
        markup.add(
            types.InlineKeyboardButton(
                text=f"{hour}:00",
                callback_data=f"hour:{hour}"
            )
        )

    markup.add(
        types.InlineKeyboardButton(
            text="Cambiar fecha",
            callback_data="change_date"
        )
    )

    bot.send_message(
        user_id,
        "Selecciona un *horario disponible*:",
        reply_markup=markup,
        parse_mode="Markdown"
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("hour:"))
def handle_hour_selection(call):
    bot.answer_callback_query(call.id)

    user_id = call.message.chat.id
    hour = int(call.data.split(":", 1)[1])

    user_data[user_id]["hour"] = hour
    user_states[user_id] = UserState.CONFIRM

    save_user_state(
        user_id,
        UserState.CONFIRM.value,
        user_data[user_id]
    )

    summary = (
        "*Resumen de la cita técnica:*\n\n"
        f"Nombre: {user_data[user_id]['name']}\n"
        #f"Teléfono: {user_data[user_id]['phone']}\n"
        f"Dirección: {user_data[user_id]['address']}\n"
        f"Fecha: {user_data[user_id]['date']}\n"
        f"Hora: {hour}:00\n"
        f"Problema: {user_data[user_id]['type']}\n\n"
        "¿Deseas confirmar la cita?"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            text="Confirmar",
            callback_data="confirm_appointment"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            text="Cambiar datos",
            callback_data="edit_appointment"
        )
    )

    bot.send_message(
        user_id,
        summary,
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "change_date")
def change_date(call):
    bot.answer_callback_query(call.id)

    user_id = call.message.chat.id
    user_states[user_id] = UserState.DATE

    save_user_state(
        user_id,
        UserState.DATE.value,
        user_data[user_id]
    )

    show_date_selection(user_id)

@bot.callback_query_handler(func=lambda call: call.data == "confirm_appointment")
def confirm_appointment(call):
    bot.answer_callback_query(call.id)

    user_id = call.message.chat.id

    if has_active_appointment(user_id):
        bot.send_message(
            user_id,
            "Ya tienes una cita activa.\n"
            "No puedes confirmar otra."
        )
        return

    appointment_data = user_data[user_id].copy()
    appointment_data["user_id"] = user_id

    success = create_appointment(appointment_data)

    if not success:
        bot.send_message(
            user_id,
            "El horario seleccionado ya fue ocupado.\n"
            "Por favor selecciona otra hora o fecha."
        )

        user_states[user_id] = UserState.DATE
        save_user_state(
            user_id,
            UserState.DATE.value,
            user_data[user_id]
        )

        show_date_selection(user_id)
        return


    bot.send_message(
        user_id,
        "*Cita confirmada con éxito*\n\n"
        f"Fecha: {appointment_data['date']}\n"
        f"Hora: {appointment_data['hour']}:00\n"
        f"Dirección: {appointment_data['address']}\n"
        f"Telefono: {appointment_data['phone']}\n\n"
        "Nuestro técnico se pondrá en contacto contigo.",
        parse_mode="Markdown"
    )

    logger.info(
        f"Cita creada: user_id={user_id}, "
        f"{appointment_data['date']} {appointment_data['hour']}:00"
    )

    user_states.pop(user_id, None)
    user_data.pop(user_id, None)

    save_user_state(user_id, None, {})


@bot.callback_query_handler(func=lambda call: call.data == "edit_appointment")
def edit_appointment(call):
    bot.answer_callback_query(call.id)

    user_id = call.message.chat.id

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            text="Cambiar fecha y hora",
            callback_data="edit_datetime"
        )
    )
    markup.add(
        types.InlineKeyboardButton(
            text="Cambiar dirección",
            callback_data="edit_address"
        )
    )

    bot.send_message(
        user_id,
        "¿Qué deseas modificar de tu cita?",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == "edit_datetime")
def edit_datetime(call):
    bot.answer_callback_query(call.id)

    user_id = call.message.chat.id

    user_states[user_id] = UserState.DATE

    save_user_state(
        user_id,
        UserState.DATE.value,
        user_data[user_id]
    )

    bot.send_message(
        user_id,
        "Vamos a cambiar la *fecha y hora* de tu cita."
    )

    show_date_selection(user_id)

@bot.callback_query_handler(func=lambda call: call.data == "edit_address")
def edit_address(call):
    bot.answer_callback_query(call.id)

    user_id = call.message.chat.id

    user_states[user_id] = UserState.ADDRESS

    save_user_state(
        user_id,
        UserState.ADDRESS.value,
        user_data[user_id]
    )

    bot.send_message(
        user_id,
        "Por favor, escribe la *nueva dirección* para la visita técnica:",
        parse_mode="Markdown"
    )





if __name__ == "__main__":
    setup_bot_commands()
    bot.infinity_polling(skip_pending=True)
    print("bot working")
