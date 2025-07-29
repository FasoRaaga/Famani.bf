from flask_wtf.file import FileField, FileAllowed
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class InscriptionAbonnementForm(FlaskForm):
    email = StringField('Adresse email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmer le mot de passe', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField("S'inscrire et s'abonner")


class ConnexionForm(FlaskForm):
    email = StringField('Adresse email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    code_admin = StringField('Code Admin (optionel)')
    remember = BooleanField('Se souvenir de moi')
    submit = SubmitField('Se connecter')

class ModifierCompteForm(FlaskForm):
    nom = StringField("Nom de la boutique", validators=[DataRequired()])
    telephone = StringField("Numéro WhatsApp", validators=[DataRequired()])
    photo = FileField("Logo", validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    nouveau_password = PasswordField("Nouveau mot de passe", validators=[Length(min=6)])
    confirm_password = PasswordField("Confirmer le mot de passe", validators=[EqualTo('nouveau_password')])
    submit = SubmitField("Mettre à jour")

