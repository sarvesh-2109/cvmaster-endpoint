from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from io import BytesIO
import os
from text_extraction import get_pdf_text, get_docx_text, preprocess_text

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "mysecretkey")

# Initialize the database connection
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///resume.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

ALLOWED_EXTENSIONS = {'pdf', 'docx'}


def allowed_file(filename):
    """Check if the file is allowed based on its extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Define the Resume model with an additional column for extracted text
class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(128), nullable=False)
    data = db.Column(db.LargeBinary, nullable=False)
    extracted_text = db.Column(db.Text, nullable=True)  # New column for extracted text


@app.route('/', methods=['GET', 'POST'])
async def home():
    """Handle resume upload and display all resumes with their extracted text."""
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            # Extract text from the file
            file_stream = BytesIO(file.read())
            if file.filename.lower().endswith('.pdf'):
                extracted_text = await get_pdf_text(file_stream)
            elif file.filename.lower().endswith('.docx'):
                extracted_text = await get_docx_text(file_stream)
            else:
                return redirect(request.url)

            # Preprocess the extracted text
            preprocessed_text = preprocess_text(extracted_text)

            # Save the resume and extracted text to the database
            new_resume = Resume(filename=file.filename, data=file_stream.getvalue(), extracted_text=preprocessed_text)
            db.session.add(new_resume)
            db.session.commit()

    # Fetch all resumes from the database
    resumes = Resume.query.all()
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


if __name__ == '__main__':
    app.run(debug=True)
