import logging
import os

from telegram import Bot
from telegram.error import BadRequest

from .schema import tirages

logger = logging.getLogger(__name__)


def setup_logging():
    root_logger = logging.getLogger("dansmabot")
    root_logger.level = logging.DEBUG
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter("{name}/{levelname} - {message}", style="{")
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(
        logging.getLevelName(os.environ.get("LOGGING_LEVEL", "DEBUG"))
    )
    root_logger.addHandler(console_handler)


def information_membre(user_id: int, chat_id: int, bot: Bot):
    try:
        chat_member = bot.get_chat_member(chat_id, user_id)
    except BadRequest:
        return None
    else:

        return chat_member.user
