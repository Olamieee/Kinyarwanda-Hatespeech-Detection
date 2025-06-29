from flask import Flask, render_template, request, redirect, url_for, flash, abort, make_response, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message, Mail
from datetime import datetime, timedelta
import joblib, re, random, string, time
import numpy as np
from sqlalchemy import func
import logging
from dotenv import load_dotenv
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_dance.contrib.google import make_google_blueprint, google


app = Flask(__name__)
app.secret_key = "replace_with_a_secret_key"

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["10 per minute"]
)

load_dotenv()

# Setup logging for debug
logging.basicConfig(level=logging.DEBUG)


#Mail Configuration
app.config['MAIL_SERVER'] = 'smtp.sendgrid.net'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'apikey' 
app.config['MAIL_PASSWORD'] = os.getenv('SENDGRID_API_KEY')
app.config['MAIL_DEFAULT_SENDER'] = 'longelee333@gmail.com'


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
    logging.debug(f"Preparing to send verification email to {email} with code {code}")
    try:
        msg = Message(
            subject="Your RHD verification code",
            recipients=[email]
        )

        # Plain text version
        msg.body = f"""
Hello,

Thanks for signing up with RHD. Please use the verification code below to complete your registration:

Verification Code: {code}

If you didn’t request this, you can safely ignore this message.

– The RHD Team
"""

        # HTML version
        msg.html = f"""
<p>Hello,</p>
<p>Thanks for signing up with <strong>RHD</strong>.</p>
<p>Please use the verification code below to complete your registration:</p>
<h2 style="color:#2e6c80;">{code}</h2>
<p>If you didn’t request this, you can safely ignore this message.</p>
<p style="margin-top:20px;">– The RHD Team</p>
"""

        mail.send(msg)
        logging.info(f"Verification email sent to {email}")
        return True
    except Exception as e:
        logging.error(f"Failed to send verification email: {e}")
        return False

# Register Google blueprint
google_bp = make_google_blueprint(
    client_id=os.getenv('GOOGLE_OAUTH_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_OAUTH_CLIENT_SECRET'),
    redirect_url='/login/google/authorized',
    scope=["profile", "email"]
)
app.register_blueprint(google_bp, url_prefix="/login")
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

def get_moderator_stats():
    total_users = User.query.count()
    total_flagged = AnalysisHistory.query.filter(
        AnalysisHistory.predicted_label.in_(["offensive", "hate"])
    ).count()

    counts_by_label = db.session.query(
        AnalysisHistory.predicted_label, func.count(AnalysisHistory.id)
    ).filter(
        AnalysisHistory.predicted_label.in_(["offensive", "hate"])
    ).group_by(AnalysisHistory.predicted_label).all()
    counts_dict = {label: count for label, count in counts_by_label}

    top_users = db.session.query(
        AnalysisHistory.user_id,
        func.count(AnalysisHistory.id).label("flagged_count")
    ).filter(
        AnalysisHistory.predicted_label.in_(["offensive", "hate"])
    ).group_by(AnalysisHistory.user_id).order_by(func.count(AnalysisHistory.id).desc()).limit(5).all()

    explanations = AnalysisHistory.query.with_entities(AnalysisHistory.explanation_words).filter(
        AnalysisHistory.predicted_label.in_(["offensive", "hate"])
    ).all()
    word_freq = {}
    for (expl,) in explanations:
        if expl:
            words = expl.split(", ")
            for w in words:
                word_freq[w] = word_freq.get(w, 0) + 1
    top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]

    week_ago = datetime.utcnow() - timedelta(days=7)
    flagged_week = AnalysisHistory.query.filter(
        AnalysisHistory.predicted_label.in_(["offensive", "hate"]),
        AnalysisHistory.timestamp >= week_ago
    ).count()

    avg_flagged_per_user = total_flagged / total_users if total_users else 0

    total_analyses = AnalysisHistory.query.count()
    flagged_percentage = (total_flagged / total_analyses * 100) if total_analyses else 0

    return {
        "total_users": total_users,
        "total_flagged": total_flagged,
        "counts_by_label": counts_dict,
        "top_users": top_users,
        "top_words": top_words,
        "flagged_week": flagged_week,
        "avg_flagged_per_user": avg_flagged_per_user,
        "flagged_percentage": flagged_percentage,
    }

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard' if current_user.role == 'user' else 'moderator_dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role', 'user')

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or email already exists.", "danger")
            return redirect(url_for("register"))

        code = generate_code()
        hashed_pw = generate_password_hash(password)
        user = User(
            full_name=full_name,
            username=username,
            email=email,
            password_hash=hashed_pw,
            verification_code=code,
            role=role
        )
        db.session.add(user)
        db.session.commit()

        sent = send_verification_email(email, code)
        if not sent:
            flash("Failed to send verification email. Please contact support.", "danger")
            logging.error("Email sending failed on registration.")
        else:
            flash("Verification code sent. Please check your email.", "info")

        return redirect(url_for("verify", username=username))
    return render_template("register.html")


@app.route('/verify/<username>', methods=['GET', 'POST'])
def verify(username):
    user = User.query.filter_by(username=username).first_or_404()

    # Cooldown timer stored in session for resend button
    resend_cooldown = session.get('resend_cooldown', 0)
    can_resend = time.time() > resend_cooldown

    if request.method == 'POST':
        if 'code' in request.form:
            if request.form['code'] == user.verification_code:
                user.is_verified = True
                user.verification_code = None
                db.session.commit()
                flash("Account verified. You may now login.", "success")
                return redirect(url_for("login"))
            else:
                flash("Incorrect code.", "danger")
        elif 'resend' in request.form and can_resend:
            new_code = generate_code()
            user.verification_code = new_code
            db.session.commit()
            sent = send_verification_email(user.email, new_code)
            if sent:
                flash("Verification code resent. Please check your email.", "info")
                session['resend_cooldown'] = time.time() + 60  # 60 seconds cooldown
            else:
                flash("Failed to resend code. Please try again later.", "danger")
        elif 'resend' in request.form and not can_resend:
            wait_time = int(resend_cooldown - time.time())
            flash(f"Please wait {wait_time} seconds before resending code.", "warning")

    return render_template("verify.html", username=username, can_resend=can_resend)

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

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if current_user.role != "user":
        return redirect(url_for('moderator_dashboard'))

    result, explanation_words, raw_text = None, [], ""

    if request.method == 'POST':
        print(request.form)  # Debug
        raw_text = request.form.get('tweet', '').strip()
        if not raw_text:
            flash("Please enter text to analyze.", "warning")
            return redirect(url_for('dashboard'))

        cleaned = preprocess_text(raw_text)
        vec = vectorizer.transform([cleaned])
        pred = model.predict(vec)[0]

        # Should output 0, 1, or 2
        label = label_encoder.inverse_transform([pred])[0]

        # Explanation
        feature_names = vectorizer.get_feature_names_out()
        coefs = model.coef_[pred]  # Use int directly
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

    stats = get_moderator_stats()

    return render_template("moderator_dashboard.html", flagged=flagged, stats=stats)

@app.route('/moderator/export')
@login_required
def export_flagged():
    if current_user.role != "moderator":
        abort(403)
    
    flagged = AnalysisHistory.query.filter(
        AnalysisHistory.predicted_label.in_(["offensive", "hate"])
    ).order_by(AnalysisHistory.timestamp.desc()).all()

    output = []
    output.append(['User ID', 'Tweet', 'Label', 'Explanation', 'Timestamp'])
    for item in flagged:
        output.append([
            item.user_id,
            item.tweet_text,
            item.predicted_label,
            item.explanation_words or "",
            item.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        ])

    response = make_response('\n'.join([','.join(map(str, row)) for row in output]))
    response.headers['Content-Disposition'] = 'attachment; filename=flagged_reports.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response

@app.route('/login/google')
def login_google():
    if not google.authorized:
        return redirect(url_for('google.login'))

    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Failed to fetch info from Google.", "danger")
        return redirect(url_for('login'))

    info = resp.json()
    email = info["email"]

    # Check if user exists
    user = User.query.filter_by(email=email).first()
    if not user:
        # New user: register
        user = User(
            full_name=info.get("name", email.split("@")[0]),
            username=email.split("@")[0],
            email=email,
            is_verified=True
        )
        db.session.add(user)
        db.session.commit()

    login_user(user)
    flash("Logged in with Google!", "success")
    return redirect(url_for("dashboard" if user.role == "user" else "moderator_dashboard"))

@app.route('/api/analyze', methods=['POST'])
@login_required  # Requires the mod/user to be logged in
def api_analyze():
    if not request.json or 'text' not in request.json:
        return jsonify({'error': 'Missing text'}), 400

    raw_text = request.json['text']
    cleaned = preprocess_text(raw_text)
    vec = vectorizer.transform([cleaned])
    pred = model.predict(vec)[0]
    label = label_encoder.inverse_transform([pred])[0]

    # Explanation (top 5 influential words)
    feature_names = vectorizer.get_feature_names_out()
    coefs = model.coef_[int(pred)]
    word_weights = vec.toarray()[0] * coefs
    top_indices = np.argsort(word_weights)[::-1][:5]
    explanation_words = [feature_names[i] for i in top_indices if vec.toarray()[0][i] > 0]

    db.session.add(AnalysisHistory(
        user_id=current_user.id if current_user.is_authenticated else None,
        tweet_text=raw_text,
        predicted_label=label,
        explanation_words=", ".join(explanation_words)
    ))
    db.session.commit()

    return jsonify({
        'label': label,
        'explanation': explanation_words
    })


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

