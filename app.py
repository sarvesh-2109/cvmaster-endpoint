from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from io import BytesIO
from markupsafe import Markup
import os
from text_extraction import get_pdf_text, get_docx_text, preprocess_text
from roast import generate_roast
from feedback import generate_feedback
from edit_resume import generate_improved_content
from ats import generate_ats_analysis
from cover_letter import generate_cover_letter

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "mysecretkey")

# Initialize the database connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'postgresql://user:password@localhost/dbname'
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
    candidate_name = db.Column(db.String(128), nullable=False)  # New column for candidate name
    roast_response = db.Column(db.Text, nullable=True)  # New column for roast response
    feedback_response = db.Column(db.Text, nullable=True)  # New column for feedback response


@app.route('/', methods=['GET', 'POST'])
async def home():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        candidate_name = request.form.get('candidate_name', 'Candidate')
        if file.filename == '' or candidate_name == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            # Extract and preprocess text
            file_stream = BytesIO(file.read())
            if file.filename.lower().endswith('.pdf'):
                extracted_text = await get_pdf_text(file_stream)
            elif file.filename.lower().endswith('.docx'):
                extracted_text = await get_docx_text(file_stream)
            else:
                return redirect(request.url)

            preprocessed_text = preprocess_text(extracted_text)

            # Save to database
            new_resume = Resume(filename=file.filename, data=file_stream.getvalue(),
                                extracted_text=preprocessed_text, candidate_name=candidate_name)
            db.session.add(new_resume)
            db.session.commit()

            return redirect(url_for('home'))

    # GET request: display upload form and existing resumes
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

    resume = Resume.query.get_or_404(resume_id)
    candidate_name = resume.candidate_name

    cover_letter = await generate_cover_letter(
        resume.extracted_text,
        job_description,
        company_name,
        position_name,
        recipient_name,
        candidate_name
    )

    return cover_letter


if __name__ == '__main__':
    app.run(debug=True)
