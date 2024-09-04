from app import app
import os
from dotenv import load_dotenv

load_dotenv()
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.getenv('SQLALCHEMY_TRACK_MODIFCATIONS')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')