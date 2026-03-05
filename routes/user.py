"""
User Routes - My Courses and Profile
"""
from flask import request, jsonify
from routes import user_bp
from models import get_supabase, Tables, Course
from utils import token_required, format_error_response, format_success_response


@user_bp.route('/profile', methods=['GET'])
@token_required
def get_profile():
    """Get user profile"""
    return jsonify(format_success_response({
        'user': request.current_user
    }))


@user_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile():
    """Update user profile"""
    data = request.get_json()
    user_id = request.current_user['id']

    allowed_fields = ['full_name', 'phone']
    update_data = {k: v for k, v in data.items() if k in allowed_fields}

    try:
        supabase = get_supabase()
        response = supabase.table(Tables.USERS).update(update_data).eq('id', user_id).execute()

        return jsonify(format_success_response({
            'user': response.data[0] if response.data else None
        }, 'Profile updated'))
    except Exception as e:
        return jsonify(format_error_response(f'Update failed: {str(e)}')), 500


@user_bp.route('/courses', methods=['GET'])
@token_required
def get_my_courses():
    """Get user's purchased courses"""
    user_id = request.current_user['id']

    try:
        supabase = get_supabase()

        # Get user_courses with course details
        response = supabase.table(Tables.USER_COURSES).select(
            '*, courses(*)'
        ).eq('user_id', user_id).eq('is_active', True).execute()

        my_courses = []
        for uc in response.data:
            course_data = uc.get('courses', {})
            my_courses.append({
                'id': uc['id'],
                'course': Course(course_data).to_dict(),
                'hwid': uc.get('hwid'),
                'purchased_at': uc['purchased_at'],
                'expires_at': uc.get('expires_at')
            })

        return jsonify(format_success_response({'courses': my_courses}))
    except Exception as e:
        return jsonify(format_error_response(f'Failed to fetch courses: {str(e)}')), 500


@user_bp.route('/courses/<course_id>/bind', methods=['POST'])
@token_required
def bind_hwid(course_id):
    """Bind HWID to a course"""
    user_id = request.current_user['id']
    data = request.get_json()
    hwid = data.get('hwid') if data else None

    if not hwid:
        return jsonify(format_error_response('HWID is required')), 400

    try:
        supabase = get_supabase()

        # Check if user owns the course
        user_course = supabase.table(Tables.USER_COURSES).select('*').eq('user_id', user_id).eq('course_id', course_id).eq('is_active', True).execute()

        if not user_course.data:
            return jsonify(format_error_response('Course not purchased')), 403

        # Check existing binding
        existing = supabase.table(Tables.HWID_BINDINGS).select('*').eq('user_id', user_id).eq('course_id', course_id).execute()

        if existing.data:
            return jsonify(format_error_response('Device already bound to this course')), 400

        # Create binding
        supabase.table(Tables.HWID_BINDINGS).insert({
            'user_id': user_id,
            'course_id': course_id,
            'hwid': hwid
        }).execute()

        # Update user_courses
        supabase.table(Tables.USER_COURSES).update({'hwid': hwid}).eq('user_id', user_id).eq('course_id', course_id).execute()

        return jsonify(format_success_response(message='Device bound successfully'))
    except Exception as e:
        return jsonify(format_error_response(f'Binding failed: {str(e)}')), 500
