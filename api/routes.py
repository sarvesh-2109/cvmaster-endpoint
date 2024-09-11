# api/routes.py
from flask import Blueprint, request, jsonify
from models import Resume, db
from text_extraction import get_pdf_text, get_docx_text, preprocess_text
from roast import generate_roast
from feedback import generate_feedback
from edit_resume import generate_improved_content
from ats import generate_ats_analysis
from io import BytesIO

api_bp = Blueprint('api', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'docx'}


def allowed_file(filename):
    """Check if the file is allowed based on its extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@api_bp.route('/api/resumes', methods=['GET'])
def get_resumes():
    """Get all resumes."""
    resumes = Resume.query.all()
    return jsonify([{
        'id': resume.id,
        'filename': resume.filename,
        'candidate_name': resume.candidate_name
    } for resume in resumes])


@api_bp.route('/api/resumes', methods=['POST'])
async def upload_resume():
    """Upload a new resume."""
    file = request.files.get('file')
    candidate_name = request.form.get('candidate_name')

    if not file or not allowed_file(file.filename) or not candidate_name:
        return jsonify({'error': 'Invalid input'}), 400

    file_stream = BytesIO(file.read())
    extracted_text = await (
        get_pdf_text(file_stream) if file.filename.lower().endswith('.pdf') else get_docx_text(file_stream))
    preprocessed_text = preprocess_text(extracted_text)

    new_resume = Resume(filename=file.filename, data=file_stream.getvalue(),
                        extracted_text=preprocessed_text, candidate_name=candidate_name)
    db.session.add(new_resume)
    db.session.commit()

    return jsonify({'message': 'Resume uploaded successfully', 'id': new_resume.id}), 201


@api_bp.route('/api/resumes/<int:resume_id>', methods=['GET'])
def get_resume(resume_id):
    """Get a specific resume by ID."""
    resume = Resume.query.get_or_404(resume_id)
    return jsonify({
        'id': resume.id,
        'filename': resume.filename,
        'candidate_name': resume.candidate_name,
        'extracted_text': resume.extracted_text
    })


@api_bp.route('/api/resumes/<int:resume_id>', methods=['DELETE'])
def delete_resume(resume_id):
    """Delete a resume by ID."""
    resume = Resume.query.get_or_404(resume_id)
    db.session.delete(resume)
    db.session.commit()
    return jsonify({'message': 'Resume deleted successfully'}), 204


@api_bp.route('/api/improve_content', methods=['POST'])
async def improve_content():
    """Improve the content of a resume."""
    content = request.json.get('content')
    if not content:
        return jsonify({'error': 'No content provided'}), 400

    improved_content = generate_improved_content(content)
    return jsonify({'improved_content': improved_content})


@api_bp.route('/api/roast/<int:resume_id>', methods=['POST'])
async def roast_resume(resume_id):
    """Generate a roast response for a specific resume."""
    resume = Resume.query.get_or_404(resume_id)
    roast_response = await generate_roast(resume.extracted_text, resume.candidate_name)
    return jsonify({'roast_response': roast_response})


@api_bp.route('/api/feedback/<int:resume_id>', methods=['POST'])
async def feedback_resume(resume_id):
    """Generate feedback for a specific resume."""
    resume = Resume.query.get_or_404(resume_id)
    feedback_response = await generate_feedback(resume.extracted_text, resume.candidate_name)
    return jsonify({'feedback_response': feedback_response})


@api_bp.route('/api/ats_analysis/<int:resume_id>', methods=['POST'])
async def ats_analysis(resume_id):
    """Perform ATS analysis on a specific resume."""
    resume = Resume.query.get_or_404(resume_id)
    job_description = request.json.get('job_description')

    if not job_description:
        return jsonify({'error': 'No job description provided'}), 400

    analysis = await generate_ats_analysis(resume.extracted_text, job_description)
    return jsonify({'analysis': analysis})