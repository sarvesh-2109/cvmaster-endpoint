from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
import random
import string
from io import BytesIO
from markupsafe import Markup
import os
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
import datetime
from sqlalchemy.sql import func

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "mysecretkey")

# Initialize the database connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'postgresql://user:password@localhost/dbname'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
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


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


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


class ContactRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=func.now())

    user = db.relationship('User', backref=db.backref('contact_requests', lazy=True))


class SupportRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, server_default=func.now())

    user = db.relationship('User', backref=db.backref('support_requests', lazy=True))


@app.route('/')
def landing():
    return render_template('landing.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegistrationForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            username = form.username.data
            email = form.email.data
            password = form.password.data

            # Create new user
            new_user = User(username=username, email=email)
            new_user.set_password(password)

            try:
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user)
                flash('Signup successful!', 'success')
                return redirect(url_for('home'))
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred: {str(e)}', 'error')

        # If form validation fails
        return render_template('signup.html', form=form)

    return render_template('signup.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('home'))

        flash('Invalid email or password', 'error')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('landing'))


def send_email(subject, recipients, body):
    try:
        msg = Message(subject,
                      recipients=recipients,
                      body=body,
                      sender=app.config['MAIL_DEFAULT_SENDER'])

        # Additional logging for debugging
        app.logger.info(f"Attempting to send email:")
        app.logger.info(f"Subject: {subject}")
        app.logger.info(f"Recipients: {recipients}")
        app.logger.info(f"Sender: {app.config['MAIL_DEFAULT_SENDER']}")

        mail.send(msg)
        app.logger.info("Email sent successfully")
        return True
    except Exception as e:
        # More detailed error logging
        app.logger.error(f"Email sending failed: {str(e)}")
        app.logger.error(f"SMTP Configuration:")
        app.logger.error(f"MAIL_SERVER: {app.config['MAIL_SERVER']}")
        app.logger.error(f"MAIL_PORT: {app.config['MAIL_PORT']}")
        app.logger.error(f"MAIL_USE_TLS: {app.config['MAIL_USE_TLS']}")
        app.logger.error(f"MAIL_USERNAME: {app.config['MAIL_USERNAME']}")

        return False


# Modify the reset_password route to use the new send_email function
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()

        if user:
            otp = ''.join(random.choices(string.digits, k=6))
            session['otp'] = otp
            session['email'] = email

            email_subject = "Your OTP for Password Reset"
            email_body = f"Your OTP is: {otp}"

            if send_email(email_subject, [email], email_body):
                flash('OTP sent to your email. Please check your inbox.', 'success')
                return redirect(url_for('verify_otp'))
            else:
                flash("Error sending email. Please try again later.", 'error')
                return redirect(url_for('reset_password'))

        flash('Email not found', 'error')
        return redirect(url_for('reset_password'))

    return render_template('reset_password.html')


@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        data = request.get_json()
        otp_entered = data.get('otp')
        if otp_entered == session.get('otp'):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False})
    return render_template('reset_password.html')


@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    try:
        app.logger.info("Change password route accessed")

        # Check if email is in session
        if 'email' not in session:
            app.logger.error("No email found in session")
            return jsonify({'success': False, 'message': 'No session email found'})

        if request.method == 'POST':
            # Log request details
            app.logger.info(f"Request is JSON: {request.is_json}")

            # Handle both JSON and form data
            if request.is_json:
                data = request.get_json()
                app.logger.info(f"Received JSON data: {data}")
                new_password = data.get('new_password')
            else:
                new_password = request.form.get('new_password')

            # Find user by email from session
            user = User.query.filter_by(email=session.get('email')).first()

            if user:
                app.logger.info(f"User found: {user.email}")
                user.set_password(new_password)
                db.session.commit()

                # Clear session after successful password reset
                session.pop('email', None)
                session.pop('otp', None)

                return jsonify({'success': True})

            app.logger.error("User not found in database")
            return jsonify({'success': False, 'message': 'User not found'})

        return render_template('reset_password.html')

    except Exception as e:
        app.logger.error(f"Error in change_password: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


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

    resumes = Resume.query.filter_by(user_id=current_user.id).all()
    return render_template('home.html', resumes=resumes)


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
                                   resume_filename=resume.filename)

        elif action == 'save':
            roast_response = request.form.get('roast_response')
            resume.roast_response = roast_response  # Save the roast response
            db.session.commit()
            flash('Roast saved successfully!', 'success')  # Add a success flash message
            return render_template('roast.html', roast_response=roast_response, candidate_name=resume.candidate_name,
                                   resume_filename=resume.filename)

        elif action == 'back_to_home':
            return redirect(url_for('home'))

    # GET request: generate roast response
    roast_response = resume.roast_response if resume.roast_response else await generate_roast(resume.extracted_text,
                                                                                              resume.candidate_name)
    return render_template('roast.html', roast_response=roast_response, candidate_name=resume.candidate_name,
                           resume_filename=resume.filename)


@app.route('/feedback/<int:resume_id>', methods=['GET', 'POST'])
async def feedback_resume(resume_id):
    resume = Resume.query.get_or_404(resume_id)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'regenerate':
            feedback_response = await generate_feedback(resume.extracted_text, resume.candidate_name)
            return render_template('feedback.html', feedback_response=feedback_response,
                                   candidate_name=resume.candidate_name, resume_filename=resume.filename)

        elif action == 'save':
            feedback_response = request.form.get('feedback_response')
            resume.feedback_response = feedback_response  # Save the feedback response
            db.session.commit()
            flash('Feedback saved successfully!', 'success')  # Add a success flash message
            return render_template('feedback.html', feedback_response=feedback_response,
                                   candidate_name=resume.candidate_name, resume_filename=resume.filename)

        elif action == 'back_to_home':
            return redirect(url_for('home'))

    # GET request: generate feedback response
    feedback_response = resume.feedback_response if resume.feedback_response else await generate_feedback(
        resume.extracted_text, resume.candidate_name)
    return render_template('feedback.html', feedback_response=feedback_response, candidate_name=resume.candidate_name,
                           resume_filename=resume.filename)


@app.route('/edit_resume/<int:resume_id>', methods=['GET', 'POST'])
async def edit_resume(resume_id):
    resume = Resume.query.get_or_404(resume_id)

    if request.method == 'GET':
        return render_template('edit_resume.html', resume_id=resume_id, candidate_name=resume.candidate_name)

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
        resumes = Resume.query.all()
        selected_resume = None
        if resume_id:
            selected_resume = Resume.query.get_or_404(resume_id)
        return render_template('ats.html', resumes=resumes, selected_resume=selected_resume)
    elif request.method == 'POST':
        resume_id = request.form.get('resume_id')
        job_description = request.form.get('job_description')

        if not resume_id or not job_description:
            return "Come on, don't leave me hanging! Please provide both a resume and a job description.", 400

        resume = Resume.query.get_or_404(resume_id)
        analysis = await generate_ats_analysis(resume.extracted_text, job_description)

        safe_analysis = Markup(f"""
        <h2 class="text-xl font-semibold mb-2">Analysis Results for {resume.candidate_name}</h2>
        <pre class="whitespace-pre-wrap">{analysis}</pre>
        """)
        return safe_analysis


@app.route('/cover_letter', methods=['GET'])
def cover_letter_form():
    resumes = Resume.query.all()
    return render_template('cover_letter.html', resumes=resumes)


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
        job_title = request.form.get('job_title')
        location = request.form.get('location')

        # Password change handling
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Notification preferences
        email_notifications = 'email_notifications' in request.form
        resume_updates = 'resume_updates' in request.form

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
            current_user.job_title = job_title
            current_user.location = location
            current_user.email_notifications = email_notifications
            current_user.resume_updates = resume_updates

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

    return render_template('profile.html')


@app.route('/contact-us', methods=['GET', 'POST'])
@login_required
def contact_us():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        try:
            # You might want to implement email sending logic here
            # For now, we'll just log the contact request
            contact = ContactRequest(
                user_id=current_user.id,
                name=name,
                email=email,
                subject=subject,
                message=message
            )
            db.session.add(contact)
            db.session.commit()

            flash('Your message has been sent successfully!', 'success')
            return redirect(url_for('contact_us'))

        except Exception as e:
            db.session.rollback()
            flash('An error occurred while sending your message', 'error')
            return redirect(url_for('contact_us'))

    return render_template('contactus.html')


@app.route('/support-us', methods=['GET', 'POST'])
@login_required
def support_us():
    if request.method == 'POST':
        donation_amount = request.form.get('donation_amount')
        custom_amount = request.form.get('custom_amount')
        payment_method = request.form.get('payment_method')

        try:
            # You might want to implement payment processing logic here
            # For now, we'll just log the support request
            amount = custom_amount if donation_amount == 'custom' else donation_amount
            support = SupportRequest(
                user_id=current_user.id,
                amount=float(amount),
                payment_method=payment_method,
                status='pending'
            )
            db.session.add(support)
            db.session.commit()

            flash('Thank you for your support! We will process your donation soon.', 'success')
            return redirect(url_for('support_us'))

        except Exception as e:
            db.session.rollback()
            flash('An error occurred while processing your support request', 'error')
            return redirect(url_for('support_us'))

    return render_template('supportus.html')


if __name__ == '__main__':
    app.run(debug=True)
