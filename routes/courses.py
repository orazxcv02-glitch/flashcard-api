"""
Course Routes
"""
from flask import request, jsonify, current_app
from routes import courses_bp
from models import get_supabase, Tables, Course
from utils import token_required, format_error_response, format_success_response
import requests


@courses_bp.route('/', methods=['GET'])
def list_courses():
    """List all active courses"""
    try:
        supabase = get_supabase()
        response = supabase.table(Tables.COURSES).select('*').eq('is_active', True).execute()

        courses = [Course(c).to_dict() for c in response.data]
        return jsonify(format_success_response({'courses': courses}))
    except Exception as e:
        return jsonify(format_error_response(f'Failed to fetch courses: {str(e)}')), 500


@courses_bp.route('/<slug>', methods=['GET'])
def get_course(slug):
    """Get course details by slug"""
    try:
        supabase = get_supabase()
        response = supabase.table(Tables.COURSES).select('*').eq('slug', slug).single().execute()

        if not response.data:
            return jsonify(format_error_response('Course not found')), 404

        course = Course(response.data)
        return jsonify(format_success_response({'course': course.to_dict()}))
    except Exception as e:
        return jsonify(format_error_response(f'Failed to fetch course: {str(e)}')), 500


@courses_bp.route('/<slug>/cards', methods=['GET'])
@token_required
def get_course_cards(slug):
    """Get flashcard data for a course (requires authentication and ownership)"""
    user_id = request.current_user['id']

    try:
        supabase = get_supabase()

        # Get course
        course_response = supabase.table(Tables.COURSES).select('*').eq('slug', slug).single().execute()
        if not course_response.data:
            return jsonify(format_error_response('Course not found')), 404

        course = Course(course_response.data)

        # Check if user owns the course
        user_course_response = supabase.table(Tables.USER_COURSES).select('*').eq('user_id', user_id).eq('course_id', course.id).eq('is_active', True).execute()

        if not user_course_response.data:
            return jsonify(format_error_response('You do not have access to this course')), 403

        # Fetch flashcard data from CDN
        data_url = course.flashcard_data_url or f"{current_app.config['DATA_BASE_URL']}{slug}.json"

        try:
            data_response = requests.get(data_url, timeout=10)
            if data_response.status_code == 200:
                flashcard_data = data_response.json()
                return jsonify(format_success_response({
                    'course': course.to_dict(include_data_url=True),
                    'flashcards': flashcard_data
                }))
            else:
                return jsonify(format_error_response('Failed to fetch flashcard data')), 500
        except requests.RequestException:
            # Try local fallback
            return jsonify(format_error_response('Flashcard data temporarily unavailable')), 503

    except Exception as e:
        return jsonify(format_error_response(f'Failed to fetch cards: {str(e)}')), 500


@courses_bp.route('/<slug>/check-access', methods=['POST'])
@token_required
def check_access(slug):
    """Check if user has access to course and bind HWID"""
    user_id = request.current_user['id']
    data = request.get_json()
    hwid = data.get('hwid') if data else None

    if not hwid:
        return jsonify(format_error_response('HWID is required')), 400

    try:
        supabase = get_supabase()

        # Get course
        course_response = supabase.table(Tables.COURSES).select('*').eq('slug', slug).single().execute()
        if not course_response.data:
            return jsonify(format_error_response('Course not found')), 404

        course = Course(course_response.data)

        # Check user_course
        user_course_response = supabase.table(Tables.USER_COURSES).select('*').eq('user_id', user_id).eq('course_id', course.id).eq('is_active', True).execute()

        if not user_course_response.data:
            return jsonify(format_error_response('Course not purchased')), 403

        user_course = user_course_response.data[0]

        # Check HWID binding
        binding_response = supabase.table(Tables.HWID_BINDINGS).select('*').eq('user_id', user_id).eq('course_id', course.id).execute()

        if binding_response.data:
            # Already bound - verify HWID matches
            binding = binding_response.data[0]
            if binding['hwid'] != hwid:
                return jsonify(format_error_response('This course is bound to a different device')), 403
        else:
            # Bind new HWID
            supabase.table(Tables.HWID_BINDINGS).insert({
                'user_id': user_id,
                'course_id': course.id,
                'hwid': hwid
            }).execute()

        # Update user_course with HWID
        supabase.table(Tables.USER_COURSES).update({'hwid': hwid}).eq('id', user_course['id']).execute()

        # Return flashcard data URL
        return jsonify(format_success_response({
            'access_granted': True,
            'course': course.to_dict(include_data_url=True),
            'flashcard_data_url': course.flashcard_data_url or f"{current_app.config['DATA_BASE_URL']}{slug}.json"
        }))

    except Exception as e:
        return jsonify(format_error_response(f'Access check failed: {str(e)}')), 500
