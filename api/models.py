# api/models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(128), nullable=False)
    data = db.Column(db.LargeBinary, nullable=False)
    extracted_text = db.Column(db.Text, nullable=True)
    candidate_name = db.Column(db.String(128), nullable=False)
    roast_response = db.Column(db.Text, nullable=True)
    feedback_response = db.Column(db.Text, nullable=True)