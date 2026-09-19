import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = "change-this-to-something-random"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'porttrack.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    