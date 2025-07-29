from app import app, db
from models import db
import os


os.makedirs("instance", exist_ok=True)


with app.app_context():
    db.create_all()
    print("base de données initialisée")