from flask import Blueprint, request, send_file, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from io import BytesIO
from app.extensions import db
from app.models import Resume, User
from app.utils.text_extraction import get_pdf_text, get_docx_text, preprocess_text

resume_bp = Blueprint('resume', __name__, url_prefix='/api/resume')

ALLOWED_EXTENSIONS = {'pdf', 'docx'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@resume_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_resume():
    current_user_id = get_jwt_identity()

    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400

    file = request.files['file']
    candidate_name = request.form.get('candidate_name', 'Candidate')

    if file.filename == '' or candidate_name == '':
        return jsonify({"status": "error", "message": "No file selected or candidate name missing"}), 400

    if file and allowed_file(file.filename):
        file_stream = BytesIO(file.read())

        if file.filename.lower().endswith('.pdf'):
            extracted_text = get_pdf_text(file_stream)
        elif file.filename.lower().endswith('.docx'):
            extracted_text = get_docx_text(file_stream)
        else:
            return jsonify({"status": "error", "message": "Invalid file type"}), 400

        preprocessed_text = preprocess_text(extracted_text)

        new_resume = Resume(
            filename=file.filename,
            data=file_stream.getvalue(),
            extracted_text=preprocessed_text,
            candidate_name=candidate_name,
            user_id=current_user_id
        )

        db.session.add(new_resume)
        db.session.commit()

        return jsonify({"status": "success", "message": "Resume uploaded successfully", "id": new_resume.id}), 201


@resume_bp.route('/get_all', methods=['GET'])
@jwt_required()
def get_all_resumes():
    current_user_id = get_jwt_identity()
    resumes = Resume.query.filter_by(user_id=current_user_id).all()

    return jsonify({
        "status": "success",
        "data": [
            {
                "id": resume.id,
                "filename": resume.filename,
                "candidate_name": resume.candidate_name
            } for resume in resumes
        ]
    }), 200


@resume_bp.route('/view/<int:resume_id>', methods=['GET'])
@jwt_required()
def view_resume(resume_id):
    current_user_id = get_jwt_identity()
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user_id).first_or_404()

    return send_file(
        BytesIO(resume.data),
        as_attachment=False,
        mimetype='application/pdf' if resume.filename.lower().endswith('.pdf')
        else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        download_name=resume.filename
    )


@resume_bp.route('/download/<int:resume_id>', methods=['GET'])
@jwt_required()
def download_resume(resume_id):
    current_user_id = get_jwt_identity()
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user_id).first_or_404()

    return send_file(
        BytesIO(resume.data),
        as_attachment=True,
        mimetype='application/pdf' if resume.filename.lower().endswith('.pdf')
        else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        download_name=resume.filename
    )


@resume_bp.route('/delete/<int:resume_id>', methods=['DELETE'])
@jwt_required()
def delete_resume(resume_id):
    current_user_id = get_jwt_identity()
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user_id).first_or_404()

    db.session.delete(resume)
    db.session.commit()

    return jsonify({"status": "success", "message": "Resume deleted successfully"}), 200


@resume_bp.route('/update/<int:resume_id>', methods=['PUT'])
@jwt_required()
def update_resume(resume_id):
    current_user_id = get_jwt_identity()
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user_id).first_or_404()

    data = request.form
    file = request.files.get('file')

    if file:
        if not allowed_file(file.filename):
            return jsonify({"status": "error", "message": "Invalid file type"}), 400

        file_stream = BytesIO(file.read())

        if file.filename.lower().endswith('.pdf'):
            extracted_text = get_pdf_text(file_stream)
        elif file.filename.lower().endswith('.docx'):
            extracted_text = get_docx_text(file_stream)
        else:
            return jsonify({"status": "error", "message": "Invalid file type"}), 400

        resume.filename = file.filename
        resume.data = file_stream.getvalue()
        resume.extracted_text = preprocess_text(extracted_text)

    resume.candidate_name = data.get('candidate_name', resume.candidate_name)

    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Resume updated successfully",
        "id": resume.id
    }), 200


@resume_bp.route('/partial_update/<int:resume_id>', methods=['PATCH'])
@jwt_required()
def partial_update_resume(resume_id):
    current_user_id = get_jwt_identity()
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user_id).first_or_404()

    data = request.form

    if 'candidate_name' in data:
        resume.candidate_name = data['candidate_name']

    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Resume partially updated successfully",
        "id": resume.id
    }), 200
