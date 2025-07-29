from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime


db = SQLAlchemy()


class Utilisateur(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    abonnement = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(20), default="user")
    is_active = db.Column(db.Boolean, default=True)
    telephone = db.Column(db.String(20))
    nom = db.Column(db.String(100))
    photo = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    produits = db.relationship('Produit', backref='utilisateur', lazy=True, cascade='all, delete-orphan')

    def peut_ajouter_produit(self):
        if self.role == 'admin':
            return True
        return len(self.produits) < 15


class Produit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    prix = db.Column(db.Float, nullable=False)
    categorie = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(120), nullable=False)
    whatsapp = db.Column(db.String(20), nullable=False)
    is_approved = db.Column(db.Boolean, default=False)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateur.id'))

class Categorie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), unique=True)

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('utilisateur.id'))

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_title = db.Column(db.String(100), default="Ma Boutique")
    theme_color = db.Column(db.String(20), default="#2c3e50")
    maintenance_mode = db.Column(db.Boolean, default=False)

class VenteFlash(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    prix = db.Column(db.Float, nullable=False)
    whatsapp = db.Column(db.String(20), nullable=False)
    date_expiration = db.Column(db.DateTime, nullable=False)

    date_creation = db.Column(db.DateTime, default=datetime.utcnow)


class evenement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.String(120), nullable=False)
    whatsapp = db.Column(db.String(20), nullable=True)
    date_expiration = db.Column(db.DateTime, nullable=True)

    date_creation = db.Column(db.DateTime, default=datetime.utcnow)