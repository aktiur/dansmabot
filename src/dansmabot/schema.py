from sqlalchemy import (
    Table,
    MetaData,
    Column,
    BigInteger,
    String,
    UniqueConstraint,
    create_engine,
)
import os
import sys


metadata = MetaData()

tirages = Table(
    "tirages",
    metadata,
    Column("salle", BigInteger),
    Column("donneur", BigInteger),
    Column("receveur", BigInteger),
    Column("nom_receveur", String),
    UniqueConstraint("salle", "donneur", name="donneur_unique"),
    UniqueConstraint("salle", "receveur", name="receveur_unique"),
)

if __name__ == "__main__":
    e = create_engine(sys.argv[1])
    metadata.create_all(e)
