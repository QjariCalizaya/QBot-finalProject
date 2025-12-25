import logging
import os
from telebot import TeleBot
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")

bot = TeleBot(TOKEN)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
