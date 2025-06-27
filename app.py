from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message, Mail
from datetime import datetime
import joblib, re, random, string, time
import numpy as np

app = Flask(__name__)
app.secret_key = "replace_with_a_secret_key"

# Mail config
app.config['MAIL_SERVER'] = 'smtp-relay.brevo.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'alongeola16@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_smtp_key'
app.config['MAIL_DEFAULT_SENDER'] = 'alongeola16@gmail.com'
mail = Mail(app)

# Database config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)

# Login setup
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

# Stopwords
kinyarwanda_stopwords = {
    "na", "ku", "mu", "ya", "y'", "n'", "bya", "cyane", "rwose",
    "kandi", "ubwo", "uko", "ntacyo", "ntukwiye", "ntacyo"
}

# Load model
model = joblib.load('model/lr_model.pkl')
vectorizer = joblib.load('model/tfidf.pkl')
label_encoder = joblib.load('model/label_encoder.pkl')

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(10), nullable=True)
    role = db.Column(db.String(20), default="user")

class AnalysisHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    tweet_text = db.Column(db.Text, nullable=False)
    predicted_label = db.Column(db.String(50))
    explanation_words = db.Column(db.String(300))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def preprocess_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'@\w+|http\S+|\d+', '', text)
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return ' '.join([w for w in text.split() if w not in kinyarwanda_stopwords])

def generate_code(length=7):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def send_verification_email(email, code):
    msg = Message("Verify your Account", recipients=[email])
    msg.body = f"Welcome! Your verification code is: {code}"
    mail.send(msg)

# Rate limiting
user_last_requests = {}

@app.before_request
def rate_limit():
    if current_user.is_authenticated:
        uid = current_user.id
        now = time.time()
        window = 60
        max_requests = 10
        timestamps = user_last_requests.get(uid, [])
        timestamps = [t for t in timestamps if now - t < window]
        if len(timestamps) >= max_requests:
            abort(429, description="Rate limit exceeded. Try again shortly.")
        timestamps.append(now)
        user_last_requests[uid] = timestamps

# Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or email already exists.", "danger")
            return redirect(url_for("register"))

        code = generate_code()
        hashed_pw = generate_password_hash(password)
        user = User(full_name=full_name, username=username, email=email,
                    password_hash=hashed_pw, verification_code=code)
        db.session.add(user)
        db.session.commit()
        send_verification_email(email, code)
        flash("Verification code sent. Please check your email.", "info")
        return redirect(url_for("verify", username=username))
    return render_template("register.html")

@app.route('/verify/<username>', methods=['GET', 'POST'])
def verify(username):
    user = User.query.filter_by(username=username).first_or_404()
    if request.method == 'POST':
        if request.form['code'] == user.verification_code:
            user.is_verified = True
            user.verification_code = None
            db.session.commit()
            flash("Account verified. You may now login.", "success")
            return redirect(url_for("login"))
        else:
            flash("Incorrect code.", "danger")
    return render_template("verify.html", username=username)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            if not user.is_verified:
                flash("Verify your email first.", "warning")
                return redirect(url_for("verify", username=user.username))
            login_user(user)
            return redirect(url_for("moderator_dashboard" if user.role == "moderator" else "dashboard"))
        flash("Invalid credentials", "danger")
    return render_template("login.html")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

@app.route('/', methods=['GET', 'POST'])
@login_required
def dashboard():
    if current_user.role != "user":
        return redirect(url_for('moderator_dashboard'))

    result, explanation_words, raw_text = None, [], ""

    if request.method == 'POST':
        raw_text = request.form['tweet']
        cleaned = preprocess_text(raw_text)
        vec = vectorizer.transform([cleaned])
        pred = model.predict(vec)[0]
        label = label_encoder.inverse_transform([pred])[0]

        # Explanation (top 5 influential words)
        feature_names = vectorizer.get_feature_names_out()
        class_index = int(pred)
        coefs = model.coef_[class_index]
        word_weights = vec.toarray()[0] * coefs
        top_indices = np.argsort(word_weights)[::-1][:5]
        explanation_words = [feature_names[i] for i in top_indices if vec.toarray()[0][i] > 0]

        db.session.add(AnalysisHistory(
            user_id=current_user.id,
            tweet_text=raw_text,
            predicted_label=label,
            explanation_words=", ".join(explanation_words)
        ))
        db.session.commit()
        result = label

    history = AnalysisHistory.query.filter_by(user_id=current_user.id).order_by(AnalysisHistory.timestamp.desc()).all()
    return render_template("dashboard.html", result=result, text=raw_text, explanation=explanation_words, history=history)

@app.route('/moderator')
@login_required
def moderator_dashboard():
    if current_user.role != "moderator":
        abort(403)
    flagged = AnalysisHistory.query.filter(
        AnalysisHistory.predicted_label.in_(["offensive", "hate"])
    ).order_by(AnalysisHistory.timestamp.desc()).all()
    return render_template("moderator_dashboard.html", flagged=flagged)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
