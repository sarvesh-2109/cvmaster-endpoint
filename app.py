from flask import Flask, request, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from io import BytesIO
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
    candidate_name = db.Column(db.String(128), nullable=False)  # New column for candidate name
    roast_response = db.Column(db.Text, nullable=True)  # New column for roast response
    feedback_response = db.Column(db.Text, nullable=True)  # New column for feedback response


@app.route('/', methods=['GET', 'POST'])
async def home():
    """
    API endpoint for home page.
    GET: Returns a list of all resumes.
    POST: Uploads a new resume.

    Returns:
        JSON response with status and data.
    """
    if request.method == 'POST':
        # Print request files for debugging
        print(request.files)

        # Check if there's any file in the request
        if not request.files:
            return jsonify({"status": "error", "message": "No file part"}), 400

        # Get the file from the request
        file = next(iter(request.files.values()))
        candidate_name = request.form.get('candidate_name', 'Candidate')

        if file.filename == '' or candidate_name == '':
            return jsonify({"status": "error", "message": "No file selected or candidate name missing"}), 400

        if file and allowed_file(file.filename):
            # Extract and preprocess text
            file_stream = BytesIO(file.read())
            if file.filename.lower().endswith('.pdf'):
                extracted_text = await get_pdf_text(file_stream)
            elif file.filename.lower().endswith('.docx'):
                extracted_text = await get_docx_text(file_stream)
            else:
                return jsonify({"status": "error", "message": "Invalid file type"}), 400

            preprocessed_text = preprocess_text(extracted_text)

            # Save to database
            new_resume = Resume(filename=file.filename, data=file_stream.getvalue(),
                                extracted_text=preprocessed_text, candidate_name=candidate_name)
            db.session.add(new_resume)
            db.session.commit()

            return jsonify({"status": "success", "message": "Resume uploaded successfully", "id": new_resume.id}), 201

    # GET request: display existing resumes
    resumes = Resume.query.all()
    return jsonify({"status": "success",
                    "data": [{"id": resume.id, "filename": resume.filename, "candidate_name": resume.candidate_name} for
                             resume in resumes]}), 200


@app.route('/view_resume/<int:resume_id>', methods=['GET'])
def view_resume(resume_id):
    """
    API endpoint to view a resume file.

    Args:
        resume_id (int): The ID of the resume to view.

    Returns:
        File response with the resume content.
    """
    resume = Resume.query.get_or_404(resume_id)
    return send_file(
        BytesIO(resume.data),
        as_attachment=False,
        mimetype='application/pdf' if resume.filename.lower().endswith(
            '.pdf') else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        download_name=resume.filename
    )


@app.route('/download_resume/<int:resume_id>', methods=['GET'])
def download_resume(resume_id):
    """
    API endpoint to download a resume file.

    Args:
        resume_id (int): The ID of the resume to download.

    Returns:
        File response with the resume content for download.
    """
    resume = Resume.query.get_or_404(resume_id)
    return send_file(
        BytesIO(resume.data),
        as_attachment=True,
        mimetype='application/pdf' if resume.filename.lower().endswith(
            '.pdf') else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        download_name=resume.filename
    )


@app.route('/delete_resume/<int:resume_id>', methods=['DELETE'])
def delete_resume(resume_id):
    """
    API endpoint to delete a resume from the database.

    Args:
        resume_id (int): The ID of the resume to delete.

    Returns:
        JSON response with status and message.
    """
    resume = Resume.query.get_or_404(resume_id)
    db.session.delete(resume)
    db.session.commit()
    return jsonify({"status": "success", "message": "Resume deleted successfully"}), 200


@app.route('/roast/<int:resume_id>', methods=['GET', 'POST'])
async def roast_resume(resume_id):
    """
    API endpoint to roast a resume.
    GET: Retrieves the existing roast or generates a new one.
    POST: Regenerates or saves a roast.

    Args:
        resume_id (int): The ID of the resume to roast.

    Returns:
        JSON response with status and roast data.
    """
    resume = Resume.query.get_or_404(resume_id)

    if request.method == 'POST':
        action = request.json.get('action')

        if action == 'regenerate':
            roast_response = await generate_roast(resume.extracted_text, resume.candidate_name)
            return jsonify({"status": "success", "roast_response": roast_response}), 200

        elif action == 'save':
            roast_response = request.json.get('roast_response')
            resume.roast_response = roast_response
            db.session.commit()
            return jsonify({"status": "success", "message": "Roast saved successfully"}), 200

    # GET request: generate roast response
    roast_response = resume.roast_response if resume.roast_response else await generate_roast(resume.extracted_text,
                                                                                              resume.candidate_name)
    return jsonify({"status": "success", "roast_response": roast_response, "candidate_name": resume.candidate_name,
                    "resume_filename": resume.filename}), 200


@app.route('/feedback/<int:resume_id>', methods=['GET', 'POST'])
async def feedback_resume(resume_id):
    """
    API endpoint to provide feedback on a resume.
    GET: Retrieves the existing feedback or generates new feedback.
    POST: Regenerates or saves feedback.

    Args:
        resume_id (int): The ID of the resume to provide feedback on.

    Returns:
        JSON response with status and feedback data.
    """
    resume = Resume.query.get_or_404(resume_id)

    if request.method == 'POST':
        action = request.json.get('action')

        if action == 'regenerate':
            feedback_response = await generate_feedback(resume.extracted_text, resume.candidate_name)
            return jsonify({"status": "success", "feedback_response": feedback_response}), 200

        elif action == 'save':
            feedback_response = request.json.get('feedback_response')
            resume.feedback_response = feedback_response
            db.session.commit()
            return jsonify({"status": "success", "message": "Feedback saved successfully"}), 200

    # GET request: generate feedback response
    feedback_response = resume.feedback_response if resume.feedback_response else await generate_feedback(
        resume.extracted_text, resume.candidate_name)
    return jsonify(
        {"status": "success", "feedback_response": feedback_response, "candidate_name": resume.candidate_name,
         "resume_filename": resume.filename}), 200


@app.route('/edit_resume/<int:resume_id>', methods=['POST'])
async def edit_resume(resume_id):
    """
    API endpoint to edit and improve resume content.

    Args:
        resume_id (int): The ID of the resume to edit.

    Expects JSON input with 'content' key containing the updated resume content.

    Returns:
        JSON response with improved content and resume data.
    """
    resume = Resume.query.get_or_404(resume_id)

    content = request.json.get('content')
    if not content:
        return jsonify({'status': 'error', 'message': 'No content provided'}), 400

    # Generate improved content
    improved_content = generate_improved_content(content)

    # Update the resume in the database with the improved content
    resume.extracted_text = improved_content
    db.session.commit()

    return jsonify({
        'status': 'success',
        'resume_id': resume_id,
        'candidate_name': resume.candidate_name,
        'improved_content': improved_content
    }), 200


@app.route('/ats_analysis', methods=['GET', 'POST'])
async def ats_analysis():
    """
    API endpoint for ATS analysis.
    GET: Returns a list of resumes for ATS analysis.
    POST: Performs ATS analysis on a resume against a job description.

    Returns:
        GET: JSON response with a list of resumes.
        POST: JSON response with the analysis results.
    """
    if request.method == 'GET':
        resumes = Resume.query.all()
        return jsonify({
            "status": "success",
            "resumes": [
                {
                    "id": resume.id,
                    "filename": resume.filename,
                    "candidate_name": resume.candidate_name
                } for resume in resumes
            ]
        }), 200

    elif request.method == 'POST':
        data = request.json
        resume_id = data.get('resume_id')
        job_description = data.get('job_description')

        if not resume_id or not job_description:
            return jsonify({
                "status": "error",
                "message": "Both resume ID and job description are required"
            }), 400

        resume = Resume.query.get_or_404(resume_id)
        analysis = await generate_ats_analysis(resume.extracted_text, job_description)

        return jsonify({
            "status": "success",
            "analysis": analysis,
            "candidate_name": resume.candidate_name
        }), 200


@app.route('/cover_letter', methods=['GET', 'POST'])
async def cover_letter():
    """
    API endpoint for cover letter functionality.

    GET: Returns a list of resumes for cover letter generation.
    POST: Generates a cover letter based on provided information.

    Returns:
        GET: JSON response with a list of resumes.
        POST: JSON response with the generated cover letter.
    """
    if request.method == 'GET':
        resumes = Resume.query.all()
        return jsonify({
            "status": "success",
            "resumes": [{"id": resume.id, "filename": resume.filename, "candidate_name": resume.candidate_name} for
                        resume in resumes]
        }), 200

    elif request.method == 'POST':
        data = request.json
        resume_id = data.get('resume_id')
        job_description = data.get('job_description')
        company_name = data.get('company_name')
        position_name = data.get('position_name')
        recipient_name = data.get('recipient_name')

        if not all([resume_id, job_description, company_name, position_name, recipient_name]):
            return jsonify({"status": "error", "message": "All fields are required"}), 400

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

        return jsonify({"status": "success", "cover_letter": cover_letter}), 200

if __name__ == '__main__':
    app.run(debug=True)
