import os
from random import shuffle

from sqlalchemy import create_engine
from sqlalchemy.sql import exists, select


from .schema import tirages


def tirer_chat(membres, chat_id, engine):
    tirage = generer_tirage(membres, chat_id)

    engine.execute(tirages.insert(), tirage)


def generer_tirage(membres, chat_id):
    membres = list(membres)

    shuffle(membres)
    n = len(membres)

    return [
        {
            "salle": chat_id,
            "donneur": membres[(i + 1) % n].id,
            "receveur": membres[i].id,
            "nom_receveur": membres[i].full_name,
        }
        for i in range(n)
    ]


def est_deja_tire(chat_id, engine):
    return (
        engine.execute(
            select(tirages.c.salle).where(tirages.c.salle == chat_id).limit(1)
        ).fetchone()
        is not None
    )


def obtenir_receveur(chat_id, donneur, engine):
    receveur = engine.execute(
        select(tirages.c.nom_receveur).where(
            tirages.c.salle == chat_id, tirages.c.donneur == donneur
        )
    ).fetchone()

    if receveur is not None:
        return receveur[0]
