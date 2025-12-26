import os
import telebot
from telebot import types
from dotenv import load_dotenv
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
        telebot.types.BotCommand(command="help", description="справка"),
        telebot.types.BotCommand(command="start", description="начать"),
        telebot.types.BotCommand(command="change", description="изменить запись"),
    ]
    bot.set_my_commands(commands)


def ensure_user_data_from_db(user_id):
    if user_id in user_data:
        return
    appointment = get_active_appointment(user_id)
    if appointment:
        user_data[user_id] = appointment
        user_data[user_id]["editing"] = True


def get_next_7_days():
    today = date.today()
    return [today + timedelta(days=i) for i in range(1, 8)]


def show_date_selection(user_id):
    markup = types.InlineKeyboardMarkup()
    for d in get_next_7_days():
        markup.add(
            types.InlineKeyboardButton(
                text=d.strftime("%A %d-%m"),
                callback_data=f"date:{d.isoformat()}"
            )
        )
    bot.send_message(
        user_id,
        "Selecciona la *fecha* para la visita técnica:",
        reply_markup=markup,
        parse_mode="Markdown"
    )


def show_hour_selection(user_id):
    selected_date = user_data[user_id]["date"]
    exclude_user = user_id if user_data[user_id].get("editing") else None
    taken_hours = get_taken_hours(selected_date, exclude_user)

    available_hours = [h for h in WORKING_HOURS if h not in taken_hours]

    if not available_hours:
        bot.send_message(
            user_id,
            "No hay horarios disponibles para esta fecha."
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

    bot.send_message(
        user_id,
        "Selecciona un *horario disponible*:",
        reply_markup=markup,
        parse_mode="Markdown"
    )


def show_edit_menu(user_id):
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


@bot.message_handler(commands=["help"])
def cmd_help(message):
    bot.send_message(
        message.chat.id,
        "/start - iniciar\n/change - editar cita"
    )


@bot.message_handler(commands=["start"])
def cmd_start(message):
    user_id = message.chat.id

    if has_active_appointment(user_id):
        ensure_user_data_from_db(user_id)
        show_edit_menu(user_id)
        return

    state, data = load_user_state(user_id)
    if state:
        user_states[user_id] = UserState(state)
        user_data[user_id] = data
        bot.send_message(user_id, "Continuamos donde lo dejaste.")
        return

    user_states[user_id] = UserState.START
    user_data[user_id] = {}

    markup = types.InlineKeyboardMarkup()
    for issue in ISSUES:
        markup.add(
            types.InlineKeyboardButton(
                text=issue,
                callback_data=f"issue:{issue}"
            )
        )

    bot.send_message(
        user_id,
        "Selecciona el problema que presentas:",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("issue:"))
def handle_issue(call):
    bot.answer_callback_query(call.id)
    user_id = call.message.chat.id
    issue = call.data.split(":", 1)[1]

    user_states[user_id] = UserState.SHOW_SOLUTIONS
    user_data[user_id]["type"] = issue

    text = "*Soluciones rápidas:*\n\n"
    for s in ISSUES[issue]:
        text += f"- {s}\n"

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            text="Solicitar técnico",
            callback_data="request_technician"
        )
    )

    bot.send_message(
        user_id,
        text,
        reply_markup=markup,
        parse_mode="Markdown"
    )


@bot.callback_query_handler(func=lambda c: c.data == "request_technician")
def request_technician(call):
    bot.answer_callback_query(call.id)
    user_id = call.message.chat.id

    user_states[user_id] = UserState.NAME
    bot.send_message(user_id, "Indica tu nombre completo:")


@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == UserState.NAME)
def handle_name(message):
    user_id = message.chat.id
    user_data[user_id]["name"] = message.text.strip()
    user_states[user_id] = UserState.PHONE
    bot.send_message(user_id, "Indica tu número de contacto:")


@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == UserState.PHONE)
def handle_phone(message):
    user_id = message.chat.id
    user_data[user_id]["phone"] = message.text.strip()
    user_states[user_id] = UserState.ADDRESS
    bot.send_message(user_id, "Indica la dirección:")


@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == UserState.ADDRESS)
def handle_address(message):
    user_id = message.chat.id
    user_data[user_id]["address"] = message.text.strip()
    user_states[user_id] = UserState.DATE

    if user_data[user_id].get("editing"):
        user_states[user_id] = UserState.CONFIRM
        save_user_state(user_id, UserState.CONFIRM.value, user_data[user_id])
        show_summary(user_id)
    else:
        user_states[user_id] = UserState.DATE
        save_user_state(user_id, UserState.DATE.value, user_data[user_id])
        show_date_selection(user_id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("date:"))
def handle_date(call):
    bot.answer_callback_query(call.id)
    user_id = call.message.chat.id
    user_data[user_id]["date"] = call.data.split(":", 1)[1]
    user_states[user_id] = UserState.HOUR
    show_hour_selection(user_id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("hour:"))
def handle_hour(call):
    bot.answer_callback_query(call.id)
    user_id = call.message.chat.id
    user_data[user_id]["hour"] = int(call.data.split(":", 1)[1])
    user_states[user_id] = UserState.CONFIRM

    d = user_data[user_id]
    text = (
        f"Nombre: {d['name']}\n"
        f"Teléfono: {d['phone']}\n"
        f"Dirección: {d['address']}\n"
        f"Fecha: {d['date']}\n"
        f"Hora: {d['hour']}:00\n"
        f"Problema: {d['type']}\n\n"
        "¿Confirmar?"
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
            text="Editar",
            callback_data="edit_appointment"
        )
    )

    bot.send_message(user_id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data == "confirm_appointment")
def confirm_appointment(call):
    bot.answer_callback_query(call.id)
    user_id = call.message.chat.id

    is_editing = user_data[user_id].get("editing", False)

    if not is_editing and has_active_appointment(user_id):
        bot.send_message(user_id, "Ya tienes una cita activa.")
        return

    if is_editing:
        success = update_appointment(user_id, user_data[user_id])
    else:
        data = user_data[user_id].copy()
        data["user_id"] = user_id
        success = create_appointment(data)

    if not success:
        bot.send_message(user_id, "Conflicto de horario.")
        show_date_selection(user_id)
        return

    bot.send_message(user_id, "Cita confirmada con éxito.")
    user_states.pop(user_id, None)
    user_data.pop(user_id, None)
    save_user_state(user_id, None, {})


@bot.callback_query_handler(func=lambda c: c.data == "edit_appointment")
def edit_appointment(call):
    bot.answer_callback_query(call.id)
    user_id = call.message.chat.id
    ensure_user_data_from_db(user_id)
    show_edit_menu(user_id)


@bot.callback_query_handler(func=lambda c: c.data == "edit_datetime")
def edit_datetime(call):
    bot.answer_callback_query(call.id)
    user_id = call.message.chat.id
    ensure_user_data_from_db(user_id)
    user_states[user_id] = UserState.DATE
    show_date_selection(user_id)


@bot.callback_query_handler(func=lambda c: c.data == "edit_address")
def edit_address(call):
    bot.answer_callback_query(call.id)
    user_id = call.message.chat.id
    ensure_user_data_from_db(user_id)
    user_states[user_id] = UserState.ADDRESS
    bot.send_message(user_id, "Indica la nueva dirección:")


@bot.message_handler(commands=["change"])
def cmd_change(message):
    user_id = message.chat.id
    if not has_active_appointment(user_id):
        bot.send_message(user_id, "No tienes citas activas.")
        return
    ensure_user_data_from_db(user_id)
    show_edit_menu(user_id)

def show_summary(user_id):
    d = user_data[user_id]

    text = (
        "*Resumen de la cita técnica:*\n\n"
        f"Nombre: {d['name']}\n"
        f"Teléfono: {d['phone']}\n"
        f"Dirección: {d['address']}\n"
        f"Fecha: {d['date']}\n"
        f"Hora: {d['hour']}:00\n"
        f"Problema: {d['type']}\n\n"
        "¿Deseas confirmar la cita?"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Confirmar", callback_data="confirm_appointment"),
        types.InlineKeyboardButton("Cambiar datos", callback_data="edit_appointment"),
    )

    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")



if __name__ == "__main__":
    setup_bot_commands()
    bot.infinity_polling(skip_pending=True)
