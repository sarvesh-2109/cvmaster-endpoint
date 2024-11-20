from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from app.extensions import db
from app.models import Resume

roast_bp = Blueprint('roast', __name__, url_prefix='/api/roast')


# Input validation schemas
class RoastActionSchema(Schema):
    action = fields.String(required=True, validate=lambda n: n in ['regenerate', 'save'])
    roast_response = fields.String(required=False, allow_none=True)


class RoastUpdateSchema(Schema):
    roast_response = fields.String(required=True)


roast_action_schema = RoastActionSchema()
roast_update_schema = RoastUpdateSchema()


@roast_bp.route('/<int:resume_id>', methods=['GET'])
@jwt_required()
def get_roast(resume_id):
    current_user_id = get_jwt_identity()
    try:
        # Ensure resume belongs to current user
        resume = Resume.query.filter_by(id=resume_id, user_id=current_user_id).first_or_404()

        if resume.roast_response:
            return jsonify({
                "status": "success",
                "roast_response": resume.roast_response,
                "candidate_name": resume.candidate_name
            }), 200

        from app.utils.roast import generate_roast
        roast_response = generate_roast(resume.extracted_text, resume.candidate_name)
        resume.roast_response = roast_response
        db.session.commit()

        return jsonify({
            "status": "success",
            "roast_response": roast_response,
            "candidate_name": resume.candidate_name
        }), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": "Database error occurred",
            "details": str(e)
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "An unexpected error occurred",
            "details": str(e)
        }), 500


@roast_bp.route('/<int:resume_id>', methods=['POST'])
@jwt_required()
def generate_or_save_roast(resume_id):
    current_user_id = get_jwt_identity()
    try:
        # Validate input
        data = request.get_json()
        roast_action_schema.load(data)

        # Ensure resume belongs to current user
        resume = Resume.query.filter_by(id=resume_id, user_id=current_user_id).first_or_404()

        action = data.get('action')
        from app.utils.roast import generate_roast

        if action == 'regenerate':
            roast_response = generate_roast(resume.extracted_text, resume.candidate_name)
            return jsonify({
                "status": "success",
                "roast_response": roast_response
            }), 200

        elif action == 'save':
            roast_response = data.get('roast_response')
            resume.roast_response = roast_response
            db.session.commit()
            return jsonify({
                "status": "success",
                "message": "Roast saved successfully"
            }), 200

    except ValidationError as err:
        return jsonify({
            "status": "error",
            "message": "Validation error",
            "details": err.messages
        }), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": "Database error occurred",
            "details": str(e)
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "An unexpected error occurred",
            "details": str(e)
        }), 500


@roast_bp.route('/<int:resume_id>', methods=['PUT'])
@jwt_required()
def update_roast(resume_id):
    current_user_id = get_jwt_identity()
    try:
        # Validate input
        data = request.get_json()
        roast_update_schema.load(data)

        # Ensure resume belongs to current user
        resume = Resume.query.filter_by(id=resume_id, user_id=current_user_id).first_or_404()

        new_roast_response = data.get('roast_response')
        resume.roast_response = new_roast_response
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Roast updated successfully",
            "roast_response": new_roast_response
        }), 200

    except ValidationError as err:
        return jsonify({
            "status": "error",
            "message": "Validation error",
            "details": err.messages
        }), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": "Database error occurred",
            "details": str(e)
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "An unexpected error occurred",
            "details": str(e)
        }), 500


@roast_bp.route('/<int:resume_id>', methods=['DELETE'])
@jwt_required()
def delete_roast(resume_id):
    current_user_id = get_jwt_identity()
    try:
        # Ensure resume belongs to current user
        resume = Resume.query.filter_by(id=resume_id, user_id=current_user_id).first_or_404()

        resume.roast_response = None
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Roast deleted successfully"
        }), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": "Database error occurred",
            "details": str(e)
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "An unexpected error occurred",
            "details": str(e)
        }), 500
