from sqlalchemy import Column, Integer, String, Float
from database import Base

class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    cbx_id = Column(String, nullable=True)

    name = Column(String, index=True)
    rating_std = Column(Float, default=1800)
    rating_rapid = Column(Float, default=1800)
    rating_blitz = Column(Float, default=1800)


class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True)