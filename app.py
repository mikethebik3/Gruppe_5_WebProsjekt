from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy.orm import relationship
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/gruppe_5_bibliotek'
app.config['SECRET_KEY'] = 'superduperhemmelig'
login_manager = LoginManager(app)
login_manager.login_view = 'login'

db = SQLAlchemy(app)


class User(UserMixin, db.Model):
    __tablename__ = 'studenter'
    id = db.Column('StudentID', db.Integer, primary_key=True)
    fornavn = db.Column('Fornavn', db.String(100), nullable=False)
    etternavn = db.Column('Etternavn', db.String(100), nullable=False)
    email = db.Column('Email', db.String(100), unique=True, nullable=False)
    password_hash = db.Column('password_hash', db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/")
def home():
    return render_template('home.html')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fornavn = request.form['fornavn']
        etternavn = request.form['etternavn']
        email = request.form['email']
        password = request.form['password']

        email_exists = User.query.filter_by(email=email).first()
        if email_exists:
            flash('E-postadressen er allerede i bruk.')
            return redirect(url_for('register'))

        new_user = User(fornavn=fornavn, etternavn=etternavn, email=email)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash('Registreringen var vellykket. Du kan nå logge inn.')
        return redirect(url_for('login'))
    return render_template('register.html')

def get_time_of_day():
    now = datetime.datetime.now()
    current_hour = now.hour

    if current_hour < 12:
        return "God morgen"
    elif 12 <= current_hour < 18:
        return "God ettermiddag"
    else:
        return "God kveld"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('profile'))
        else:
            flash('Feil brukernavn eller passord.')
    return render_template('login.html')


@app.route('/profile')
@login_required
def profile():
    greeting = get_time_of_day()  # Kaller funksjonen for å få hilsen basert på tid på døgnet
    return render_template('profile.html', time_of_day=greeting, fornavn=current_user.fornavn, etternavn=current_user.etternavn)



@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/available_books')
@login_required
def available_books():
    # Hent alle bøker som ikke er lånt ut for øyeblikket
    available_books = Bøker.query.filter(~Bøker.ISBN.in_(db.session.query(LånteBøker.ISBN).filter_by(Levert=False))).all()
    return render_template('available_books.html', books=available_books)

@app.route('/borrow_book', methods=['POST'])
@login_required
def borrow_book():
    isbn = request.form['isbn']
    user_id = current_user.id
    lån_dato = datetime.datetime.now().date()  # Korrekt bruk av datetime med full referanse
    retur_dato = lån_dato + datetime.timedelta(days=30)  # Anta 30 dagers lån

    # Opprett en ny låneoppføring
    nytt_lån = LånteBøker(StudentID=user_id, ISBN=isbn, LånDato=lån_dato, ReturDato=retur_dato, Levert=False)
    db.session.add(nytt_lån)
    db.session.commit()

    flash('Du har nå lånt boken.')
    return redirect(url_for('available_books'))


@app.route('/my_loans')
@login_required
def my_loans():
    # Hent alle aktive lån for den innloggede brukeren
    user_loans = LånteBøker.query.filter_by(StudentID=current_user.id, Levert=False).all()
    return render_template('my_loans.html', loans=user_loans)


class Bøker(db.Model):
    ISBN = db.Column(db.BigInteger, primary_key=True, nullable=False)
    Tittel = db.Column(db.String(100), nullable=False)
    Forfatter = db.Column(db.String(100), nullable=False)
    Sjanger = db.Column(db.String(100), nullable=False)

    # Definerer relasjonen til LånteBøker
    lånte_bøker = relationship("LånteBøker", back_populates="bok")


class LånteBøker(db.Model):
    LånID = db.Column(db.Integer, primary_key=True, nullable=False, autoincrement=True)
    StudentID = db.Column(db.Integer, nullable=False)
    ISBN = db.Column(db.BigInteger, db.ForeignKey('bøker.ISBN'), nullable=False)
    LånDato = db.Column(db.Date, nullable=False)
    ReturDato = db.Column(db.Date, nullable=True)
    Levert = db.Column(db.Boolean, nullable=False, default=False)

    # Definerer relasjonen til Bøker
    bok = relationship("Bøker", back_populates="lånte_bøker")


class Tidsskrifter(db.Model):
    TidsskriftID = db.Column(db.Integer, primary_key=True)
    Tittel = db.Column(db.String(100), nullable=False)
    Utgiver = db.Column(db.String(100), nullable=False)
    Kategori = db.Column(db.String(100), nullable=False)

    # Definerer relasjonen til LånteTidsskrifter
    lånte_tidsskrifter = relationship("LånteTidsskrifter", back_populates="tidsskrift")


class LånteTidsskrifter(db.Model):
    T_LånID = db.Column(db.Integer, primary_key=True, nullable=False, autoincrement=True)
    StudentID = db.Column(db.Integer, nullable=False)
    TidsskriftID = db.Column(db.Integer, db.ForeignKey('tidsskrifter.TidsskriftID'), nullable=False)
    LånDato = db.Column(db.Date, nullable=False)
    ReturDato = db.Column(db.Date, nullable=True)
    Levert = db.Column(db.Boolean, nullable=False, default=False)

    # Definerer relasjonen til Tidsskrifter
    tidsskrift = relationship("Tidsskrifter", back_populates="lånte_tidsskrifter")

@app.route('/innlevering', methods=['GET', 'POST'])
@login_required
def innlevering():
    if request.method == 'POST':
        selected_items = request.form.getlist('item_id')
        for item_id in selected_items:
            if item_id.startswith('bok_'):
                loan = LånteBøker.query.get(int(item_id.replace('bok_', '')))
            elif item_id.startswith('tidsskrift_'):
                loan = LånteTidsskrifter.query.get(int(item_id.replace('tidsskrift_', '')))
            if loan:
                loan.Levert = True
                loan.ReturDato = datetime.datetime.now().date()  # Korrigert bruk av datetime
                db.session.commit()
        return redirect(url_for('profile'))

    loans_bøker = LånteBøker.query.filter_by(StudentID=current_user.id, Levert=False).all()
    loans_tidsskrifter = LånteTidsskrifter.query.filter_by(StudentID=current_user.id, Levert=False).all()
    last_delivered_items = LånteBøker.query.filter_by(StudentID=current_user.id, Levert=True).order_by(
        LånteBøker.ReturDato.desc()).limit(5).all() + \
        LånteTidsskrifter.query.filter_by(StudentID=current_user.id, Levert=True).order_by(
            LånteTidsskrifter.ReturDato.desc()).limit(5).all()
    return render_template('innlevering.html', loans_bøker=loans_bøker, loans_tidsskrifter=loans_tidsskrifter, last_delivered_items=last_delivered_items)


if __name__ == "__main__":
    app.run(debug=True)
