from sqlalchemy import Column, String
from app.db.session import Base


class User(Base):
    __tablename__ ="users"
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True)
    password=Column(String, nullable=True)
    totp_secret = Column(String, nullable=True)