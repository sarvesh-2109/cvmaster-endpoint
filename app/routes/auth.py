from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.models import User
import requests

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"status": "error", "message": "Username already exists"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"status": "error", "message": "Email already exists"}), 400

    hashed_password = generate_password_hash(password)
    new_user = User(username=username, email=email, password=hashed_password)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"status": "success", "message": "User registered successfully"}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401

    access_token = create_access_token(identity=user.id)
    return jsonify({"status": "success", "access_token": access_token}), 200


@auth_bp.route('/google_login', methods=['POST'])
def google_login():
    data = request.get_json()
    token = data.get('token')

    response = requests.get(f'https://oauth2.googleapis.com/tokeninfo?id_token={token}')

    if response.status_code != 200:
        return jsonify({"status": "error", "message": "Invalid Google token"}), 401

    google_info = response.json()

    email = google_info['email']

    user = User.query.filter_by(email=email).first()

    if user:
        access_token = create_access_token(identity=user.id)
        return jsonify({"status": "success", "access_token": access_token}), 200
    else:
        username = google_info.get('name') or email.split('@')[0]  # Use name from Google or part of email as username

        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash("google_auth")  # Placeholder password for Google users
        )

        db.session.add(new_user)
        db.session.commit()

        access_token = create_access_token(identity=new_user.id)
        return jsonify({"status": "success", "access_token": access_token}), 201
