from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from io import BytesIO
import os

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "mysecretkey")  # Set a secret key for session management

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///resume.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# Define the Resume model
class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(128), nullable=False)
    data = db.Column(db.LargeBinary, nullable=False)


# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'docx'}


def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/home', methods=['GET', 'POST'])
async def home():
    """Handle resume upload and display all resumes."""
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            # Read the file content
            file_data = file.read()
            # Save the file content to the database
            new_resume = Resume(filename=file.filename, data=file_data)
            db.session.add(new_resume)
            db.session.commit()

    # Fetch all resumes from the database
    resumes = Resume.query.all()
    return render_template('home.html', resumes=resumes)


@app.route('/view_resume/<int:resume_id>')
async def view_resume(resume_id):
    """Stream the resume file without downloading."""
    resume = Resume.query.get_or_404(resume_id)
    return send_file(
        BytesIO(resume.data),
        as_attachment=False,
        mimetype='application/pdf' if resume.filename.lower().endswith(
            '.pdf') else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        download_name=resume.filename
    )


@app.route('/download_res/<int:resume_id>')
async def download_resume(resume_id):
    """Provide the resume file for download."""
    resume = Resume.query.get_or_404(resume_id)
    return send_file(
        BytesIO(resume.data),
        as_attachment=True,
        mimetype='application/pdf' if resume.filename.lower().endswith(
            '.pdf') else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        download_name=resume.filename
    )


@app.route('/delete_res/<int:resume_id>', methods=['POST'])
async def delete_resume(resume_id):
    """Delete a specific resume from the database."""
    resume = Resume.query.get_or_404(resume_id)
    db.session.delete(resume)
    db.session.commit()
    return redirect(url_for('home'))


@app.route('/')
def index():
    """Render the home page."""
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
