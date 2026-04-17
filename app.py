import os
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "astro-secret-key-2024")

# ── Base de données ─────────────────────────────────────────────────────────
# MySQL / MariaDB en production : définir DATABASE_URL dans l'environnement
# Ex : mysql+pymysql://user:password@localhost/astronomie
# Par défaut : SQLite pour le développement local
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///astronomie.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ── Modèles ─────────────────────────────────────────────────────────────────

class User(db.Model):
    __tablename__ = "users"
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80),  unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class AppareilPhoto(db.Model):
    __tablename__ = "appareils_photo"
    id          = db.Column(db.Integer, primary_key=True)
    marque      = db.Column(db.String(80),  nullable=False)
    modele      = db.Column(db.String(120), nullable=False)
    date_sortie = db.Column(db.String(10),  nullable=False)
    score       = db.Column(db.Integer,     nullable=False)
    categorie   = db.Column(db.String(50),  nullable=False)


class Telescope(db.Model):
    __tablename__ = "telescopes"
    id          = db.Column(db.Integer, primary_key=True)
    marque      = db.Column(db.String(80),  nullable=False)
    modele      = db.Column(db.String(120), nullable=False)
    date_sortie = db.Column(db.String(10),  nullable=False)
    score       = db.Column(db.Integer,     nullable=False)
    categorie   = db.Column(db.String(50),  nullable=False)


class Photographie(db.Model):
    __tablename__ = "photographies"
    id          = db.Column(db.Integer, primary_key=True)
    titre       = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    url         = db.Column(db.String(500), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    auteur      = db.relationship("User", backref="photographies")


# ── Décorateur d'authentification ────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Veuillez vous connecter pour accéder à cette page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ── Routes : Authentification ────────────────────────────────────────────────

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm", "")

        if not username or not email or not password:
            flash("Tous les champs sont obligatoires.", "danger")
        elif password != confirm:
            flash("Les mots de passe ne correspondent pas.", "danger")
        elif User.query.filter_by(username=username).first():
            flash("Ce nom d'utilisateur est déjà pris.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("Cet email est déjà utilisé.", "danger")
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Compte créé avec succès ! Vous pouvez vous connecter.", "success")
            return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session["user_id"]  = user.id
            session["username"] = user.username
            flash(f"Bienvenue, {user.username} !", "success")
            return redirect(url_for("index"))
        else:
            flash("Identifiants incorrects.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for("login"))


# ── Routes : Contenu du site ─────────────────────────────────────────────────

@app.route("/appareils-photo")
@login_required
def appareils_photo():
    appareils  = AppareilPhoto.query.order_by(AppareilPhoto.categorie, AppareilPhoto.score.desc()).all()
    categories = ["Amateur", "Amateur sérieux", "Professionnel"]
    return render_template("appareils_photo.html", appareils=appareils, categories=categories)


@app.route("/telescopes")
@login_required
def telescopes():
    tous       = Telescope.query.order_by(Telescope.categorie, Telescope.score.desc()).all()
    categories = ["Télescopes pour enfants", "Automatisés", "Télescopes complets"]
    return render_template("telescopes.html", telescopes=tous, categories=categories)


@app.route("/photographies")
@login_required
def photographies():
    photos = Photographie.query.order_by(Photographie.created_at.desc()).all()
    return render_template("photographies.html", photos=photos)


# ── Données de démonstration ─────────────────────────────────────────────────

def seed_data():
    if AppareilPhoto.query.count() == 0:
        appareils = [
            AppareilPhoto(marque="Canon",  modele="EOS 2000D",     date_sortie="2018-02-15", score=3, categorie="Amateur"),
            AppareilPhoto(marque="Nikon",  modele="D3500",         date_sortie="2018-08-30", score=4, categorie="Amateur"),
            AppareilPhoto(marque="Sony",   modele="Alpha a6000",   date_sortie="2014-02-12", score=3, categorie="Amateur"),
            AppareilPhoto(marque="Canon",  modele="EOS 90D",       date_sortie="2019-08-28", score=4, categorie="Amateur sérieux"),
            AppareilPhoto(marque="Nikon",  modele="Z50",           date_sortie="2019-10-10", score=4, categorie="Amateur sérieux"),
            AppareilPhoto(marque="Sony",   modele="Alpha a7 III",  date_sortie="2018-02-26", score=5, categorie="Amateur sérieux"),
            AppareilPhoto(marque="Canon",  modele="EOS R5",        date_sortie="2020-07-30", score=5, categorie="Professionnel"),
            AppareilPhoto(marque="Nikon",  modele="Z9",            date_sortie="2021-10-28", score=5, categorie="Professionnel"),
            AppareilPhoto(marque="ZWO",    modele="ASI2600MC Pro", date_sortie="2020-05-01", score=5, categorie="Professionnel"),
        ]
        db.session.bulk_save_objects(appareils)

    if Telescope.query.count() == 0:
        telescopes_data = [
            Telescope(marque="Celestron",        modele="FirstScope 76",      date_sortie="2015-03-01", score=3, categorie="Télescopes pour enfants"),
            Telescope(marque="National Geographic",modele="80/400",           date_sortie="2017-09-01", score=2, categorie="Télescopes pour enfants"),
            Telescope(marque="Bresser",           modele="Junior 60/700 AZ",  date_sortie="2019-01-15", score=3, categorie="Télescopes pour enfants"),
            Telescope(marque="Celestron",         modele="NexStar 5SE",       date_sortie="2015-06-01", score=4, categorie="Automatisés"),
            Telescope(marque="Meade",             modele="LX65 6",            date_sortie="2016-04-01", score=4, categorie="Automatisés"),
            Telescope(marque="Sky-Watcher",       modele="Evostar 80 AZ-GTe", date_sortie="2018-03-01", score=4, categorie="Automatisés"),
            Telescope(marque="Celestron",         modele="CPC 1100 GPS",      date_sortie="2010-01-01", score=5, categorie="Télescopes complets"),
            Telescope(marque="Meade",             modele="LX200 12",          date_sortie="2012-06-01", score=5, categorie="Télescopes complets"),
            Telescope(marque="Sky-Watcher",       modele="Dobson 16 Truss",   date_sortie="2020-08-01", score=5, categorie="Télescopes complets"),
        ]
        db.session.bulk_save_objects(telescopes_data)

    if Photographie.query.count() == 0:
        photos = [
            Photographie(titre="Nébuleuse d'Orion",      description="Capturée avec un Canon EOS R5 et un Celestron CPC 1100.",
                url="https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/Orion_Nebula_-_Hubble_2006_mosaic_18000.jpg/800px-Orion_Nebula_-_Hubble_2006_mosaic_18000.jpg"),
            Photographie(titre="Galaxie d'Andromède",    description="M31, la grande galaxie spirale voisine.",
                url="https://upload.wikimedia.org/wikipedia/commons/thumb/9/98/Andromeda_Galaxy_%28with_h-alpha%29.jpg/800px-Andromeda_Galaxy_%28with_h-alpha%29.jpg"),
            Photographie(titre="Amas des Pléiades",      description="M45, amas ouvert dans le Taureau.",
                url="https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Pleiades_large.jpg/800px-Pleiades_large.jpg"),
            Photographie(titre="Jupiter et ses lunes",   description="Jupiter avec Io, Europe, Ganymède et Callisto.",
                url="https://upload.wikimedia.org/wikipedia/commons/thumb/2/2b/Jupiter_and_its_shrunken_Great_Red_Spot.jpg/800px-Jupiter_and_its_shrunken_Great_Red_Spot.jpg"),
            Photographie(titre="Voie Lactée",            description="La bande de notre galaxie depuis les Alpes.",
                url="https://upload.wikimedia.org/wikipedia/commons/thumb/0/01/Milky_Way_Night_Sky_Black_Rock_Desert_Nevada.jpg/800px-Milky_Way_Night_Sky_Black_Rock_Desert_Nevada.jpg"),
            Photographie(titre="Nébuleuse de la Rosette",description="Nébuleuse d'émission dans la Licorne.",
                url="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Rosette_Nebula_-_GigaGalaxy_Zoom_%28ESO%29.jpg/800px-Rosette_Nebula_-_GigaGalaxy_Zoom_%28ESO%29.jpg"),
        ]
        db.session.bulk_save_objects(photos)

    db.session.commit()


with app.app_context():
    db.create_all()
    seed_data()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
