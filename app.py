from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from text_extraction import get_pdf_text, get_docx_text, preprocess_text
from roast import generate_roast
from feedback import generate_feedback
from edit_resume import generate_improved_content
from ats import generate_ats_analysis
from cover_letter import generate_cover_letter
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
from io import BytesIO
from markupsafe import Markup
import shutil
import threading
import time
import os
from sqlalchemy.sql import func
from oauthlib.oauth2 import WebApplicationClient
import requests
import json
from functools import wraps
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "mysecretkey")

# Initialize the database connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'postgresql://user:password@localhost/dbname'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USERNAME', 'cvmaster.in@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('EMAIL_SENDER', 'cvmaster.in@gmail.com')
mail = Mail(app)

ALLOWED_EXTENSIONS = {'pdf', 'docx'}

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Ensure default value is set
app.config['GOOGLE_OAUTH_REDIRECT'] = os.environ.get('GOOGLE_OAUTH_REDIRECT',
                                                     'http://localhost:5000/login/google/callback')

# Enable insecure transport in development
if app.config['GOOGLE_OAUTH_REDIRECT'] and (
        'localhost' in app.config['GOOGLE_OAUTH_REDIRECT'] or '127.0.0.1' in app.config['GOOGLE_OAUTH_REDIRECT']):
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# OAuth2 client setup
client = WebApplicationClient(GOOGLE_CLIENT_ID)


def get_google_provider_cfg():
    try:
        return requests.get(GOOGLE_DISCOVERY_URL).json()
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error fetching Google provider config: {str(e)}")
        return None


# Set the path to the FAISS directory
FAISS_DIR = os.path.join(os.path.dirname(__file__), 'faiss_indices')

# Set the interval to delete the directory (e.g., one hour)
DELETE_INTERVAL_MS = 1 * 60 * 60 * 1000  # 1 hour


# Function to delete Faiss Indices
def deleteFAISSDirectory():
    try:
        # Delete the directory recursively
        if os.path.exists(FAISS_DIR):
            shutil.rmtree(FAISS_DIR)
        print('FAISS directory deleted successfully.')
    except (OSError, shutil.Error) as e:
        print(f'Error deleting FAISS directory: {e}')


def start_faiss_cleanup():
    while True:
        deleteFAISSDirectory()
        time.sleep(DELETE_INTERVAL_MS / 1000)  # Sleep for the specified interval


# Start the FAISS cleanup in a separate thread
cleanup_thread = threading.Thread(target=start_faiss_cleanup)
cleanup_thread.daemon = True
cleanup_thread.start()


def allowed_file(filename):
    """Check if the file is allowed based on its extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Define the User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Define the Resume model
class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(128), nullable=False)
    data = db.Column(db.LargeBinary, nullable=False)
    extracted_text = db.Column(db.Text, nullable=True)
    candidate_name = db.Column(db.String(128), nullable=False)
    roast_response = db.Column(db.Text, nullable=True)
    feedback_response = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('resumes', lazy=True))


# Registration form using WTForms
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email is already in use. Please choose a different one.')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(message='Enter a valid email')])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


@app.route('/')
def landing():
    return render_template('landing.html', layout_type='navbar')


@app.route("/login/google")
def google_login():
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    if not google_provider_cfg:
        flash("Error connecting to Google", "error")
        return redirect(url_for("login"))

    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use the configured redirect URI
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=app.config['GOOGLE_OAUTH_REDIRECT'],
        scope=["openid", "email", "profile"],
    )
    return redirect(request_uri)


@app.route("/login/google/callback")
def callback():
    try:
        # Get authorization code Google sent back
        code = request.args.get("code")
        if not code:
            flash("No authorization code received from Google", "error")
            return redirect(url_for("login"))

        google_provider_cfg = get_google_provider_cfg()
        if not google_provider_cfg:
            flash("Error connecting to Google", "error")
            return redirect(url_for("login"))

        token_endpoint = google_provider_cfg["token_endpoint"]

        # Prepare and send token request
        token_url, headers, body = client.prepare_token_request(
            token_endpoint,
            authorization_response=request.url,
            redirect_url=app.config['GOOGLE_OAUTH_REDIRECT'],
            code=code,
        )

        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
        )

        # Parse the tokens
        client.parse_request_body_response(json.dumps(token_response.json()))

        # Get user info from Google
        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        uri, headers, body = client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(uri, headers=headers, data=body)

        if userinfo_response.json().get("email_verified"):
            users_email = userinfo_response.json()["email"]
            users_name = userinfo_response.json()["given_name"]
        else:
            flash("Google authentication failed", "error")
            return redirect(url_for("login"))

        # Create or get user
        user = User.query.filter_by(email=users_email).first()
        if not user:
            user = User(
                username=users_name,
                email=users_email,
            )
            user.set_password(os.urandom(24).hex())
            db.session.add(user)
            db.session.commit()

        login_user(user)
        return redirect(url_for("home"))

    except Exception as e:
        app.logger.error(f"Error in Google callback: {str(e)}")
        flash("An error occurred during Google login", "error")
        return redirect(url_for("login"))


def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegistrationForm()
    if request.method == 'GET':
        return render_template('signup.html', form=form, layout_type='navbar')

    # Handle POST request
    if request.method == 'POST':
        data = request.get_json()

        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data received'
            })

        # Validate form data
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not all([username, email, password]):
            return jsonify({
                'status': 'error',
                'message': 'All fields are required.'
            })

        # Check if email already exists
        if User.query.filter_by(email=email).first():
            return jsonify({
                'status': 'error',
                'message': 'Email already exists.'
            })

        # Generate OTP
        otp = generate_otp()

        # Store signup data and OTP in session
        session['signup_data'] = {
            'username': username,
            'email': email,
            'password': password,
            'otp': otp,
            'created_at': datetime.utcnow().isoformat()
        }

        try:
            # Create and send email
            msg = Message('Verify your email',
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[email])

            msg.body = f'''To verify your email address, please use the following OTP:

{otp}

This OTP will expire in 10 minutes.
If you did not make this request, please ignore this email.'''

            mail.send(msg)

            return jsonify({
                'status': 'success',
                'message': 'OTP has been sent to your email.'
            })

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': 'Error sending verification email. Please try again.'
            })


@app.route('/verify_signup_otp', methods=['POST'])
def verify_signup_otp():
    data = request.get_json()
    user_otp = data.get('otp')

    if not user_otp:
        return jsonify({
            'status': 'error',
            'message': 'OTP is required.'
        })

    signup_data = session.get('signup_data')
    if not signup_data:
        return jsonify({
            'status': 'error',
            'message': 'Signup session expired. Please try again.'
        })

    # Check if OTP has expired (10 minutes)
    created_at = datetime.fromisoformat(signup_data['created_at'])
    if datetime.utcnow() - created_at > timedelta(minutes=10):
        session.pop('signup_data', None)
        return jsonify({
            'status': 'error',
            'message': 'OTP has expired. Please try again.'
        })

    # Verify OTP
    if user_otp != signup_data['otp']:
        return jsonify({
            'status': 'error',
            'message': 'Invalid OTP. Please try again.'
        })

    try:
        # Create new user
        new_user = User(
            username=signup_data['username'],
            email=signup_data['email']
        )
        new_user.set_password(signup_data['password'])

        db.session.add(new_user)
        db.session.commit()

        # Log in the user
        login_user(new_user)

        # Clear signup session data
        session.pop('signup_data', None)

        return jsonify({
            'status': 'success',
            'message': 'Account created successfully!'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Error creating account. Please try again.'
        })


@app.route('/check_email_exists', methods=['POST'])
def check_email_exists():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'exists': False})

    user = User.query.filter_by(email=email).first()
    return jsonify({'exists': bool(user)})


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            # Check if it's an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'redirect_url': url_for('home')})
            return redirect(url_for('home'))

        # Invalid credentials
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Invalid email or password'})

    # For normal GET requests, render the template
    return render_template('login.html', form=form, layout_type='navbar')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('landing'))


def send_email(subject, recipients, body):
    try:
        msg = Message(subject, recipients=recipients, body=body)
        mail.send(msg)
        return True
    except Exception as e:
        return False


@app.route('/reset_password', methods=['POST'])
def reset_password():
    data = request.get_json()
    email = data.get('email')
    if not email:
        return jsonify({
            'status': 'error',
            'message': 'Please enter an email address'
        })
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({
            'status': 'error',
            'message': 'No account found with this email address'
        })
    otp = ''.join(random.choices(string.digits, k=6))
    session['otp'] = otp
    session['email'] = email
    email_subject = "Your OTP for Password Reset"
    email_body = f"Your OTP is: {otp}"
    if send_email(email_subject, [email], email_body):
        return jsonify({
            'status': 'success',
            'message': 'OTP sent to your email. Please check your inbox.'
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Error sending email. Please try again later.'
        })


@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        data = request.get_json()
        otp_entered = data.get('otp')
        if otp_entered == session.get('otp'):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False})
    return render_template('verify_otp.html')


@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'email' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            new_password = data.get('new_password')
            confirm_password = data.get('confirm_password')
        else:
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            return jsonify({'success': False, 'message': 'Passwords do not match'})
        user = User.query.filter_by(email=session.get('email')).first()
        if user:
            user.set_password(new_password)
            db.session.commit()
            session.pop('email', None)
            session.pop('otp', None)
            flash('Password updated successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        return jsonify({'success': False, 'message': 'User not found'})
    return render_template('reset_password.html', layout_type='navbar')


@app.route('/home', methods=['GET', 'POST'])
@login_required
async def home():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(url_for('home'))

        file = request.files['file']
        candidate_name = request.form.get('candidate_name', current_user.username)

        if file.filename == '' or candidate_name == '':
            flash('No selected file or candidate name', 'error')
            return redirect(url_for('home'))

        if file and allowed_file(file.filename):
            file_stream = BytesIO(file.read())

            try:
                if file.filename.lower().endswith('.pdf'):
                    extracted_text = await get_pdf_text(file_stream)
                elif file.filename.lower().endswith('.docx'):
                    extracted_text = await get_docx_text(file_stream)
                else:
                    flash('Invalid file type', 'error')
                    return redirect(url_for('home'))

                preprocessed_text = preprocess_text(extracted_text)

                new_resume = Resume(
                    filename=file.filename,
                    data=file_stream.getvalue(),
                    extracted_text=preprocessed_text,
                    candidate_name=candidate_name,
                    user_id=current_user.id
                )

                db.session.add(new_resume)
                db.session.commit()
                flash('Resume uploaded successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error uploading resume: {str(e)}', 'error')

            return redirect(url_for('home'))

    resumes = Resume.query.filter_by(user_id=current_user.id).order_by(Resume.id.desc()).all()
    return render_template('home.html', resumes=resumes, layout_type='authenticated')


@app.route('/view_resume/<int:resume_id>')
def view_resume(resume_id):
    """View a resume file."""
    resume = Resume.query.get_or_404(resume_id)
    return send_file(
        BytesIO(resume.data),
        as_attachment=False,
        mimetype='application/pdf' if resume.filename.lower().endswith(
            '.pdf') else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        download_name=resume.filename
    )


@app.route('/download_resume/<int:resume_id>')
def download_resume(resume_id):
    """Download a resume file."""
    resume = Resume.query.get_or_404(resume_id)
    return send_file(
        BytesIO(resume.data),
        as_attachment=True,
        mimetype='application/pdf' if resume.filename.lower().endswith(
            '.pdf') else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        download_name=resume.filename
    )


@app.route('/delete_resume/<int:resume_id>', methods=['POST'])
def delete_resume(resume_id):
    """Delete a resume from the database."""
    resume = Resume.query.get_or_404(resume_id)
    db.session.delete(resume)
    db.session.commit()
    return redirect(url_for('home'))


@app.route('/roast/<int:resume_id>', methods=['GET', 'POST'])
async def roast_resume(resume_id):
    resume = Resume.query.get_or_404(resume_id)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'regenerate':
            roast_response = await generate_roast(resume.extracted_text, resume.candidate_name)
            return render_template('roast.html', roast_response=roast_response, candidate_name=resume.candidate_name,
                                   resume_filename=resume.filename, layout_type='authenticated')

        elif action == 'save':
            roast_response = request.form.get('roast_response')
            resume.roast_response = roast_response  # Save the roast response
            db.session.commit()
            flash('Roast saved successfully!', 'success')  # Add a success flash message
            return render_template('roast.html', roast_response=roast_response, candidate_name=resume.candidate_name,
                                   resume_filename=resume.filename, layout_type='authenticated')

        elif action == 'back_to_home':
            return redirect(url_for('home'))

    # GET request: generate roast response
    roast_response = resume.roast_response if resume.roast_response else await generate_roast(resume.extracted_text,
                                                                                              resume.candidate_name)
    return render_template('roast.html', roast_response=roast_response, candidate_name=resume.candidate_name,
                           resume_filename=resume.filename, layout_type='authenticated')


@app.route('/feedback/<int:resume_id>', methods=['GET', 'POST'])
async def feedback_resume(resume_id):
    resume = Resume.query.get_or_404(resume_id)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'regenerate':
            feedback_response = await generate_feedback(resume.extracted_text, resume.candidate_name)
            return render_template('feedback.html', feedback_response=feedback_response,
                                   candidate_name=resume.candidate_name, resume_filename=resume.filename,
                                   layout_type='authenticated')

        elif action == 'save':
            feedback_response = request.form.get('feedback_response')
            resume.feedback_response = feedback_response  # Save the feedback response
            db.session.commit()
            flash('Feedback saved successfully!', 'success')  # Add a success flash message
            return render_template('feedback.html', feedback_response=feedback_response,
                                   candidate_name=resume.candidate_name, resume_filename=resume.filename,
                                   layout_type='authenticated')

        elif action == 'back_to_home':
            return redirect(url_for('home'))

    # GET request: generate feedback response
    feedback_response = resume.feedback_response if resume.feedback_response else await generate_feedback(
        resume.extracted_text, resume.candidate_name)
    return render_template('feedback.html', feedback_response=feedback_response, candidate_name=resume.candidate_name,
                           resume_filename=resume.filename, layout_type='authenticated')


@app.route('/edit_resume/<int:resume_id>', methods=['GET', 'POST'])
async def edit_resume(resume_id):
    resume = Resume.query.get_or_404(resume_id)

    if request.method == 'GET':
        return render_template('edit_resume.html', resume_id=resume_id, candidate_name=resume.candidate_name,
                               layout_type='authenticated')

    elif request.method == 'POST':
        content = request.json.get('content')
        if not content:
            return jsonify({'error': 'No content provided'}), 400

        improved_content = generate_improved_content(content)
        return jsonify({'improved_content': improved_content})


@app.route('/ats_analysis', methods=['GET', 'POST'])
@app.route('/ats_analysis/<int:resume_id>', methods=['GET'])
async def ats_analysis(resume_id=None):
    if request.method == 'GET':
        resumes = Resume.query.filter_by(user_id=current_user.id).all()
        selected_resume = None
        if resume_id:
            selected_resume = Resume.query.get_or_404(resume_id)
        return render_template('ats.html', resumes=resumes, selected_resume=selected_resume,
                               layout_type='authenticated')
    elif request.method == 'POST':
        resume_id = request.form.get('resume_id')
        job_description = request.form.get('job_description')

        if not resume_id or not job_description:
            return "Come on, don't leave me hanging! Please provide both a resume and a job description.", 400

        resume = Resume.query.get_or_404(resume_id)
        analysis = await generate_ats_analysis(resume.extracted_text, job_description)

        safe_analysis = Markup(f"""
                    <div class="space-y-6">
                        <h2 class="text-2xl font-semibold text-black-900">Analysis Results for {resume.candidate_name}</h2>
                        <div class="prose prose-blue max-w-none">
                            <div class="text-black-900 leading-relaxed">
                                {analysis}
                            </div>
                        </div>
                    </div>
                """)
        return safe_analysis


@app.route('/cover_letter', methods=['GET'])
def cover_letter_form():
    resumes = Resume.query.filter_by(user_id=current_user.id).all()
    return render_template('cover_letter.html', resumes=resumes, layout_type='authenticated')


@app.route('/generate_cover_letter', methods=['POST'])
async def generate_cover_letter_route():
    resume_id = request.form.get('resume_id')
    job_description = request.form.get('job_description')
    company_name = request.form.get('company_name')
    position_name = request.form.get('position_name')
    recipient_name = request.form.get('recipient_name')
    platform_name = request.form.get('platform_name')
    resume = Resume.query.get_or_404(resume_id)
    candidate_name = resume.candidate_name

    cover_letter = await generate_cover_letter(
        resume.extracted_text,
        job_description,
        company_name,
        position_name,
        recipient_name,
        platform_name,
        candidate_name
    )
    return cover_letter


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Extract form data
        username = request.form.get('username')
        email = request.form.get('email')
        # job_title = request.form.get('job_title')
        # location = request.form.get('location')

        # Password change handling
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # # Notification preferences
        # email_notifications = 'email_notifications' in request.form
        # resume_updates = 'resume_updates' in request.form

        # Validate and update user profile
        try:
            # Check if username or email already exists
            existing_user = User.query.filter(
                (User.username == username) | (User.email == email)
            ).first()

            if existing_user and existing_user.id != current_user.id:
                flash('Username or email already exists', 'error')
                return redirect(url_for('profile'))

            # Update basic profile info
            current_user.username = username
            current_user.email = email
            # current_user.job_title = job_title
            # current_user.location = location
            # current_user.email_notifications = email_notifications
            # current_user.resume_updates = resume_updates

            # Password change logic
            if current_password and new_password and confirm_password:
                if not current_user.check_password(current_password):
                    flash('Current password is incorrect', 'error')
                    return redirect(url_for('profile'))

                if new_password != confirm_password:
                    flash('New passwords do not match', 'error')
                    return redirect(url_for('profile'))

                current_user.set_password(new_password)

            db.session.commit()
            flash('Profile updated successfully', 'success')
            return redirect(url_for('profile'))

        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating profile', 'error')
            return redirect(url_for('profile'))

    return render_template('profile.html', layout_type='authenticated')


@app.route('/contact-us', methods=['GET', 'POST'])
def contact_us():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        # Construct email body
        email_body = f"""
        New contact form submission from:
        Name: {name}
        Email: {email}

        Message:
        {message}
        """

        # Send email to admin
        admin_email = app.config['MAIL_DEFAULT_SENDER']  # or another admin email
        if send_email(subject, [admin_email], email_body):
            flash('Your message has been sent successfully!', 'success')
        else:
            flash('There was an error sending your message. Please try again later.', 'error')

        return redirect(url_for('contact_us'))

    if current_user.is_authenticated:
        layout_type = 'authenticated'
    else:
        layout_type = 'non-authenticated'
    return render_template('contactus.html', layout_type=layout_type)


@app.route('/support-us', methods=['GET', 'POST'])
def support_us():
    if current_user.is_authenticated:
        layout_type = 'authenticated'
    else:
        layout_type = 'non-authenticated'
    return render_template('supportus.html', layout_type=layout_type)


if __name__ == '__main__':
    app.run(debug=True)
