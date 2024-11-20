from flask import request, jsonify
from werkzeug.security import check_password_hash
from app.models import User


def validate_user_registration(data):
    """Validate user registration data."""
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return {"status": "error", "message": "Missing required fields"}, 400

    if User.query.filter_by(username=username).first():
        return {"status": "error", "message": "Username already exists"}, 400

    if User.query.filter_by(email=email).first():
        return {"status": "error", "message": "Email already exists"}, 400

    return None  # No validation errors


def validate_login(data):
    """Validate user login data."""
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return {"status": "error", "message": "Missing username or password"}, 400

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password, password):
        return {"status": "error", "message": "Invalid credentials"}, 401

    return user  # Return the user object if valid


def validate_resume_upload(request):
    """Validate resume upload request."""
    if 'file' not in request.files:
        return {"status": "error", "message": "No file part"}, 400

    file = request.files['file']
    candidate_name = request.form.get('candidate_name', '').strip()

    if file.filename == '' or candidate_name == '':
        return {"status": "error", "message": "No file selected or candidate name missing"}, 400

    # Check for allowed file types (this should match your allowed_file function)
    allowed_extensions = {'pdf', 'docx'}
    if '.' not in file.filename or file.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return {"status": "error", "message": "Invalid file type"}, 400

    return None