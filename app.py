from flask import Flask, render_template, redirect, url_for, flash, request
from models import db, Produit, Utilisateur, Categorie, Log, Settings, VenteFlash, evenement
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from forms import InscriptionAbonnementForm, ConnexionForm, ModifierCompteForm
import os
from werkzeug.utils import secure_filename
from config import Config
from functools import wraps
from _datetime import datetime

from datetime import datetime

app = Flask(__name__)
app.config.from_object('config.Config')
db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)

app.secret_key = 'ton_secret_key_ici'



@app.route('/mon_compte', methods=['GET', 'POST'])
def mon_compte():
    form = InscriptionAbonnementForm()

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        if Utilisateur.query.filter_by(email=email).first():
            flash("Cet email est déjà utilisé.", "danger")
            return redirect(url_for('mon_compte'))


        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        user = Utilisateur(email=email, password=hashed_pw, abonnement=True)
        db.session.add(user)
        db.session.commit()

        login_user(user)

        flash("Compte créé et abonnement activé avec succès.", "success")
        return redirect(url_for('compte'))

    return render_template("mon_compte.html", form=form)



@login_manager.user_loader
def load_user(user_id):
    return Utilisateur.query.get(int(user_id))


@app.route('/')
def accueil():
    categories = [
        "Services", "Mode", "Électronique", "Maison", "Beauté", "Alimentation",
        "Santé", "Art", "Sport", "Évènement", "Énergie renouvelable", "Technologie", "Autres"
    ]

    produits_par_categorie = {}

    for cat in categories:
        produit = Produit.query.filter_by(categorie=cat).first()
        if produit:
            produits_par_categorie[cat] = produit

    now = datetime.utcnow()
    ventes_flash = VenteFlash.query.filter(VenteFlash.date_expiration > now).all()

    now = datetime.utcnow()
    events = evenement.query.filter(evenement.date_expiration > now).all()

    return render_template('accueil.html',
        produits_par_categorie=produits_par_categorie,
        categories=categories,
        ventes_flash=ventes_flash,
        events=events
    )


@app.before_request
def cleanup_expired_flash_sales():
    now = datetime.utcnow()
    expired = VenteFlash.query.filter(VenteFlash.date_expiration <= now).all()

    for sale in expired:
        db.session.delete(sale)

    if expired:
        db.session.commit()


@app.before_request
def cleanup_expired_event():
    now = datetime.utcnow()
    expired = evenement.query.filter(evenement.date_expiration <= now).all()

    for sale in expired:
        db.session.delete(sale)

    if expired:
        db.session.commit()


def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

@app.route('/explorer')
def explorer():
    # Récupérer les paramètres de recherche, de tri et de catégorie depuis l'URL
    search_query = request.args.get('q', '')  # Recherche par description
    sort_by = request.args.get('sort_by', '')  # Tri par prix
    categorie = request.args.get('categorie')  # Filtrage par catégorie

    # Filtrer les produits par catégorie si spécifiée
    if categorie:
        produits_categorie = Produit.query.filter_by(categorie=categorie).all()
        nom_categorie = categorie
    else:
        produits_categorie = []
        nom_categorie = ""

    # Appliquer la recherche par description
    produits = Produit.query.filter(
        Produit.description.contains(search_query)

    )
    # Appliquer le tri des produits
    if sort_by == 'prix_asc':
        produits = produits.order_by(Produit.prix.asc())  # Tri par prix croissant
    elif sort_by == 'prix_desc':
        produits = produits.order_by(Produit.prix.desc())  # Tri par prix décroissant

    # Récupérer la liste des catégories depuis la base de données
    categories = db.session.query(Produit.categorie).distinct().all()
    categories = [c[0] for c in categories]  # Extraire les chaînes de caractères

    return render_template("explorer.html",
                           produits=produits,
                           produits_categorie=produits_categorie,
                           categories=categories,
                           nom_categorie=nom_categorie,
                           search=search_query,
                           sort_by=sort_by)


@app.route('/ajouter_produit', methods=['GET', 'POST'])
@login_required
def ajouter_produit():
    if not current_user.abonnement and current_user.role != 'admin':
        flash("Vous devez être abonné pour publier un produit.", "warning")
        return redirect(url_for('mon_compte'))

    if not current_user.peut_ajouter_produit():
        flash("Vous avez atteint la limite de 15 produits. Supprimez des produits pour en ajouter de nouveaux.",
              "warning")
        return redirect(url_for('mes_produits'))

    if request.method == 'POST':
        nom = request.form['nom']
        description = request.form['description']
        prix = float(request.form['prix'])
        categorie = request.form['categorie']
        whatsapp = request.form['whatsapp']

        image = request.files['image']
        if image.filename != '':
            filename = secure_filename(image.filename)
            image_path = (os.path.join("static/images", filename))
            image.save(image_path)
        else:
            image_path = "images/default.png"


        produit = Produit(nom=nom, description=description, prix=prix,
                          categorie=categorie, whatsapp=whatsapp,
                          image=image_path, utilisateur_id=current_user.id)
        db.session.add(produit)
        db.session.commit()
        flash("Produit ajouté avec succès !", "success")
        return redirect(url_for('explorer'))

    return render_template('ajouter_produit.html')


@app.route('/connexion', methods=['GET', 'POST'])
def connexion():
    if current_user.is_authenticated :
        return redirect(url_for('compte'))

    form = ConnexionForm()

    if form.validate_on_submit():
        user = Utilisateur.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):

            if form.code_admin.data and form.code_admin.data == Config.ADMIN_CODE:
                user.role = "admin"
                db.session.commit()
                flash("Connexion admin réussie !", "success")
                login_user(user, remember=form.remember.data)
                return redirect(url_for('admin_dashboard'))
            else:
                login_user(user, remember=form.remember.data)
                flash("Connexion réussie !", "success")
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('compte'))
        else:
            flash('Identifiants incorrects.', 'danger')

    return render_template('connexion.html', form=form)


@app.route('/compte')
@login_required
def compte():
    return render_template('compte.html', utilisateur=current_user)

@app.route('/modifier_compte', methods=['GET', 'POST'])
@login_required
def modifier_compte():
    form = ModifierCompteForm()

    if form.validate_on_submit():
        current_user.nom = form.nom.data
        current_user.telephone = form.telephone.data

        if form.photo.data:
            if not os.path.exists('static/profils'):
                os.makedirs('static/profils')
            photo_file = secure_filename(form.photo.data.filename)
            photo_path = os.path.join('static/profils', photo_file)
            form.photo.data.save(photo_path)
            current_user.photo = photo_file

        if form.nouveau_password.data:
            hashed_pw = bcrypt.generate_password_hash(form.nouveau_password.data).decode('utf-8')
            current_user.password = hashed_pw

        db.session.commit()
        flash("Informations mises à jour.", "success")
        return redirect(url_for('compte'))

    form.nom.data = current_user.nom
    form.telephone.data = current_user.telephone

    return render_template('modifier_compte.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Vous êtes déconnecté.', 'success')
    return redirect(url_for('connexion'))


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            flash("Accès refusé.", "danger")
            return redirect(url_for('connexion'))
        return f(*args, **kwargs)
    return decorated_function

# Dashboard admin
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    users = Utilisateur.query.all()
    produits = Produit.query.all()
    return render_template('admin_dashboard.html', users=users, produits=produits)

# Supprimer un utilisateur
@app.route('/admin/delete_user/<int:user_id>')
@admin_required
def delete_user(user_id):
    user = Utilisateur.query.get(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("Compte supprimé.", "success")
    return redirect(url_for('admin_dashboard'))

# Supprimer un produit
@app.route('/admin/delete_product/<int:product_id>')
@admin_required
def delete_product(product_id):
    produit = Produit.query.get(product_id)
    db.session.delete(produit)
    db.session.commit()
    flash("Produit supprimé.", "success")
    return redirect(url_for('admin_dashboard'))


# ---------------------------
# Gestion Utilisateurs
# ---------------------------

@app.route('/admin/users')
@admin_required
def manage_users():
    users = Utilisateur.query.order_by(Utilisateur.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


@app.route('/admin/toggle_user/<int:user_id>')
@admin_required
def toggle_user(user_id):
    user = Utilisateur.query.get(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    log_action(f"Modification statut utilisateur {user.email}")
    return redirect(url_for('manage_users'))


# ---------------------------
# Gestion Produits
# ---------------------------

@app.route('/admin/products')
@admin_required
def manage_products():
    products = Produit.query.filter_by(is_approved=False).all()
    return render_template('admin/products.html', products=products)


@app.route('/admin/approve_product/<int:product_id>')
@admin_required
def approve_product(product_id):
    product = Produit.query.get(product_id)
    product.is_approved = True
    db.session.commit()
    log_action(f"Approbation produit #{product.id}")
    return redirect(url_for('manage_products'))

# ---------------------------
# Statistiques
# ---------------------------

@app.route('/admin/stats')
@admin_required
def admin_stats():
    stats = {
        'users': Utilisateur.query.count(),
        'active_users': Utilisateur.query.filter_by(is_active=True).count(),
        'products': Produit.query.count(),
        'pending_products': Produit.query.filter_by(is_approved=False).count(),
        'categories': Categorie.query.count()
    }
    return render_template('admin/stats.html', stats=stats)


# ---------------------------
# Paramètres du Site
# ---------------------------

@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def site_settings():
    settings = Settings.query.first()
    if not settings:
        settings = Settings()
        db.session.add(settings)
        db.session.commit()

    if request.method == 'POST':
        settings.site_title = request.form.get('site_title')
        settings.theme_color = request.form.get('theme_color')
        settings.maintenance_mode = 'maintenance_mode' in request.form
        db.session.commit()
        log_action("Modification des paramètres du site")

    return render_template('admin/settings.html', settings=settings)


# ---------------------------
# Journal d'activité
# ---------------------------

@app.route('/admin/activity_log')
@admin_required
def activity_log():
    logs = Log.query.order_by(Log.timestamp.desc()).limit(100).all()
    return render_template('admin/activity_log.html', logs=logs)


def log_action(action):
    log = Log(
        action=action,
        user_id=current_user.id
    )
    db.session.add(log)
    db.session.commit()

@app.before_request
def check_maintenance():
    settings = Settings.query.first()
    if settings and settings.maintenance_mode:
        if request.path.startswith('/admin') and current_user.role != 'admin':
            os.abort(503)


@app.route('/admin/ventes_flash', methods=['GET', 'POST'])
@admin_required
def manage_flash_sales():
    if request.method == 'POST':
        # Récupérer les données du formulaire
        description = request.form.get('description')
        prix = float(request.form.get('prix'))
        whatsapp = request.form.get('whatsapp')
        date_expiration = datetime.strptime(request.form.get('date_expiration'), '%Y-%m-%dT%H:%M')
        image = request.files['image']

        if image.filename != '':
            filename = secure_filename(image.filename)
            image_path = os.path.join("static/images", filename)
            image.save(image_path)
            image_url = filename
        else:
            flash("Veuillez ajouter une image", "danger")
            return redirect(url_for('manage_flash_sales'))

        vf = VenteFlash(
            description=description,
            prix=prix,
            whatsapp=whatsapp,
            date_expiration=date_expiration,
            image=image_url
        )
        db.session.add(vf)
        db.session.commit()
        flash("Vente flash ajoutée", "success")
        return redirect(url_for('manage_flash_sales'))

    # Récupérer toutes les ventes flash
    ventes = VenteFlash.query.order_by(VenteFlash.date_expiration.asc()).all()
    return render_template('admin/ventes_flash.html', ventes=ventes)


@app.route('/admin/ventes_flash/delete/<int:id>')
@admin_required
def delete_flash_sale(id):
    vf = VenteFlash.query.get(id)
    db.session.delete(vf)
    db.session.commit()
    flash("Vente flash supprimée", "success")
    return redirect(url_for('manage_flash_sales'))


@app.route('/admin/events', methods=['GET', 'POST'])
@admin_required
def manage_event():
    if request.method == 'POST':
        # Récupérer les données du formulaire
        whatsapp = request.form.get('whatsapp')
        date_expiration = datetime.strptime(request.form.get('date_expiration'), '%Y-%m-%dT%H:%M')
        image = request.files['image']

        if image.filename != '':
            filename = secure_filename(image.filename)
            image_path = os.path.join("static/images", filename)
            image.save(image_path)
            image_url = filename
        else:
            flash("Veuillez ajouter une image", "danger")
            return redirect(url_for('manage_flash_sales'))

        ev = evenement(
            whatsapp=whatsapp,
            date_expiration=date_expiration,
            image=image_url
        )
        db.session.add(ev)
        db.session.commit()
        flash("Evenement ajoutée", "success")
        return redirect(url_for('manage_event'))

    # Récupérer toutes les ventes flash
    ajouts = evenement.query.order_by(evenement.date_expiration.asc()).all()
    return render_template('admin/events.html', ajouts=ajouts)


@app.route('/admin/events/delete/<int:id>')
@admin_required
def delete_event(id):
    ev = evenement.query.get(id)
    db.session.delete(ev)
    db.session.commit()
    flash("Evenement supprimée", "success")
    return redirect(url_for('manage_event'))


@app.route('/admin/utilisateurs-produits')
@admin_required
def admin_utilisateurs_produits():
    # Récupérer tous les utilisateurs avec leurs produits
    utilisateurs = Utilisateur.query.options(db.joinedload(Utilisateur.produits)).all()

    return render_template('admin/utilisateurs_produits.html',
                           utilisateurs=utilisateurs)


@app.route('/admin/supprimer_utilisateur/<int:user_id>', methods=['POST'])
@admin_required
def supprimer_utilisateur(user_id):
    utilisateur = Utilisateur.query.get_or_404(user_id)

    # Supprimer tous les produits associés
    produits = Produit.query.filter_by(utilisateur_id=user_id).all()
    for produit in produits:
        # Supprimer l'image si ce n'est pas l'image par défaut
        if produit.image != "images/default.png":
            try:
                os.remove(os.path.join('static', produit.image))
            except Exception as e:
                app.logger.error(f"Erreur suppression image: {str(e)}")
        db.session.delete(produit)

    # Supprimer la photo de profil si elle existe
    if utilisateur.photo and utilisateur.photo != "default.png":
        try:
            os.remove(os.path.join('static/profils', utilisateur.photo))
        except Exception as e:
            app.logger.error(f"Erreur suppression photo profil: {str(e)}")

    # Supprimer l'utilisateur
    db.session.delete(utilisateur)
    db.session.commit()

    flash(f"L'utilisateur {utilisateur.email} et tous ses produits ont été supprimés.", "success")
    return redirect(url_for('admin_utilisateurs_produits'))


@app.route('/mes_produits')
@login_required
def mes_produits():
    produits = Produit.query.filter_by(utilisateur_id=current_user.id).all()
    nombre_produits = len(produits)
    return render_template('mes_produits.html',
                           produits=produits,
                           nombre_produits=nombre_produits)


@app.route('/supprimer_produit/<int:id>', methods=['POST'])
@login_required
def supprimer_produit(id):
    produit = Produit.query.get_or_404(id)

    # Vérifier que l'utilisateur est propriétaire du produit
    if produit.utilisateur_id != current_user.id:
        flash("Vous n'êtes pas autorisé à supprimer ce produit.", "danger")
        return redirect(url_for('mes_produits'))

    db.session.delete(produit)
    db.session.commit()
    flash("Produit supprimé avec succès.", "success")
    return redirect(url_for('mes_produits'))