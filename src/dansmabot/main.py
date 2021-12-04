import os
import logging
from random import choice

from sqlalchemy import create_engine

from telegram import ChatMemberLeft, Update
from telegram.constants import PARSEMODE_MARKDOWN_V2, PARSEMODE_HTML
from telegram.ext import (
    Updater,
    CallbackContext,
    CommandHandler,
    PicklePersistence,
    ChatMemberHandler,
)

from .tirages import est_deja_tire, tirer_chat, obtenir_receveur
from .utils import setup_logging, information_membre

setup_logging()

logger = logging.getLogger(__name__)


engine = create_engine(os.environ.get("DATABASE_URL", "sqlite:///database.sqlite3"))

persistence = PicklePersistence(filename=os.environ.get("PERSISTENCE_FILE", "bot.dat"))
updater = Updater(
    token=os.environ["BOT_TOKEN"], use_context=True, persistence=persistence
)
dispatcher = updater.dispatcher

MESSAGE_SIGNALEMENT = [
    "Bien vu, {} !",
    "Ok, je note ça, {}.",
    "{}, c'est un joli nom !",
    "{} ? C'est noté.",
    "Je t'ajoute à la liste, {}.",
    "Merci {}, j'ai rajouté ton nom.",
    "C'est parfait, {}.",
    "{}, un de plus. Il en manque encore ?",
    "{}... ça se prononce comme ça s'écrit ?",
    "Ah, {}, je sais parfaitement à qui vous attribuer !",
]

MESSAGE_RECEVEUR = [
    "Cette année, votre victi... bienheureux destinataire de votre générosité est : {} !",
    "Ne le dites à personne, mais c'est {} qui va recevoir votre cadeau !",
    "Vous avez de la chance, vous avez tiré {} !",
    "Alors, regardons la liste... Vous devez offrir votre cadeau à {} !",
]

MESSAGE_DEJA_VU = [
    "Hum... C'est étrange, je vous ai déjà dans ma liste, {}.",
    "Vous vous êtes déjà signalé avant {}, je me trompe ?",
    "Une seule fois, ça suffit, {}.",
    "Vous tenez à avoir deux cadeaux à offrir, {}, c'est ça ?",
]

MESSAGE_DEJA_TIRE = [
    'Le tirage a déjà été fait ! Il faut <a href="{url}">venir me voir</a> maintenant pour savoir à qui vous devez offir.',
    "Heu, c'est un problème de vue ou de mémoire, {prenom} ? J'ai déjà <a href=\"{url}\">fait le tirage</a>...",
    "Ce n'est pas parce que <a href=\"{url}\">votre tirage</a> ne vous plaît pas qu'on va retirer tout le monde, {prenom}...",
    "Alors, le principe, c'est qu'on le fait une seule fois le tirage, {prenom}. Il faut accepter <a href=\"{url}\">votre choix aléatoire</a> maintenant.",
]


def details_membres(chat, context):
    # mettre à jour la liste des membres pour éliminer ceux qui ne sont plus dans le chat
    membres = [
        u
        for u in (
            information_membre(user_id, chat.id, context.bot)
            for user_id in context.chat_data.get("membres", set())
        )
        if u and not u.is_bot
    ]

    context.chat_data["membres"] = {u.id for u in membres}

    return membres


def bot_url(chat_id):
    return f"https://t.me/DansMaBot?start={chat_id}"


def start(update: Update, context: CallbackContext):
    if update.effective_chat.type != "private":
        return

    try:
        target_chat_id = int(context.args[0])
    except (ValueError, IndexError):
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Normalement, il faut arriver d'un groupe où il y a eu tirage au sort !",
        )
        return

    receveur = obtenir_receveur(target_chat_id, update.message.from_user.id, engine)

    if receveur is None:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Vous n'étiez pas présent·e pour le tirage au sort, désolé :/",
        )
    else:
        message = choice(MESSAGE_RECEVEUR)

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message.format(receveur),
        )


def commande_sesignaler(update: Update, context: CallbackContext):
    chat = update.effective_chat

    if chat.type != "group":
        context.bot.send_message(
            chat.id,
            text="Mais non ! j'ai besoin que vous vous signalez **dans le groupe** !",
            parse_mode=PARSEMODE_MARKDOWN_V2,
        )
    else:
        user = update.message.from_user
        if user.id in context.chat_data.get("membres", set()):
            message = choice(MESSAGE_DEJA_VU)
            context.bot.send_message(
                chat_id=chat.id, text=message.format(user.first_name)
            )
        else:
            context.chat_data.setdefault("membres", set()).add(user.id)
            message = choice(MESSAGE_SIGNALEMENT)
            context.bot.send_message(
                chat_id=chat.id, text=message.format(user.first_name)
            )

            compte = chat.get_member_count()
            membres = details_membres(chat, context)
            difference = compte - len(membres) - 1
            if difference in [15, 10, 5]:
                context.bot.send_message(
                    chat_id=chat.id,
                    text=f"Il ne me manque plus que {difference} personnes !",
                )
            elif difference == 1:
                context.bot.send_message(
                    chat_id=chat.id,
                    text=f"Ouh ! Plus qu'une seule personne et on y est !",
                )
            elif difference == 0:
                tirer_chat(membres, chat.id, engine)

                context.bot.send_message(
                    chat_id=chat.id,
                    text=f"J'ai tout le monde ! C'est parfait, je lance le tirage au sort...\n"
                    'Et voilà ! <a href="{bot_url(chat.id)}">Venez me voir en privé</a> pour savoir à qui offrir un message !',
                    parse_mode=PARSEMODE_HTML,
                )


def commande_tirage(update: Update, context: CallbackContext):
    chat = update.effective_chat
    user = update.message.from_user

    if chat.type == "private":
        context.bot.send_message(
            chat.id,
            text="Il faut me demander ça dans un groupe, pas en privé !",
        )
        return

    if est_deja_tire(chat.id, engine):
        message = choice(MESSAGE_DEJA_TIRE)
        context.bot.send_message(
            chat_id=chat.id,
            text=message.format(url=bot_url(chat.id), prenom=user.first_name),
            parse_mode=PARSEMODE_HTML,
        )
        return

    member_count = chat.get_member_count() - 1

    # mettre à jour la liste des membres pour éliminer ceux qui ne sont plus dans le chat
    membres = details_membres(chat, context)

    if len(membres) != member_count:
        context.bot.send_message(
            chat.id,
            text=f"Je n'ai pas encore identifié tout le monde ! {member_count - len(membres)} personnes doivent encore se signaler.",
        )
        return

    tirer_chat(membres, chat.id, engine)

    context.bot.send_message(
        chat.id,
        text=f'Et voilà, le tirage est effectué ! <a href="{bot_url(chat.id)}">Venez me demander en privé à qui vous devez faire un cadeau.</a>',
        parse_mode=PARSEMODE_HTML,
    )


def handle_join(update: Update, context: CallbackContext):
    chat_status = update.my_chat_member

    if isinstance(chat_status.old_chat_member, ChatMemberLeft):
        logger.debug(
            "Rejoint le chat {}, ajouté par {}".format(
                chat_status.chat.title,
                chat_status.from_user.username or chat_status.username,
                chat_status.new_chat_member,
                chat_status.old_chat_member,
            )
        )
        context.chat_data["membres"] = {chat_status.from_user.id}
        # on vient de rejoindre un chat !
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Ho ho ho ! Merci {chat_status.from_user.first_name} de m'avoir invité. "
            "Malheureusement, ma vue n'est pas bonne et <strong>je ne peux voir que les "
            "personnes qui font l'effort de /sesignaler</strong> ! Pourriez-vous tous le faire "
            "pour que je puisse lancer le tirage au sort ? Je le fais dès qu'on a tout le monde !",
            parse_mode=PARSEMODE_HTML,
        )


start_handler = CommandHandler("start", start)
dispatcher.add_handler(start_handler)

signalement_handler = CommandHandler("sesignaler", commande_sesignaler)
dispatcher.add_handler(signalement_handler)

tirage_handler = CommandHandler("tirage", commande_tirage)
dispatcher.add_handler(tirage_handler)

join_handler = ChatMemberHandler(handle_join)
dispatcher.add_handler(join_handler)


if __name__ == "__main__":
    updater.start_polling()
