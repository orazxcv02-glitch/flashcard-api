"""
Authentication Routes
"""
from flask import request, jsonify, current_app
from routes import auth_bp
from models import get_supabase, Tables, User
from utils import (
    generate_token, verify_token, token_required,
    validate_email, format_error_response, format_success_response
)
from gotrue.errors import AuthApiError


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()

    # Validate input
    if not data:
        return jsonify(format_error_response('No data provided')), 400

    email = data.get('email')
    password = data.get('password')
    username = data.get('username')
    full_name = data.get('full_name')
    phone = data.get('phone')

    if not email or not password:
        return jsonify(format_error_response('Email and password are required')), 400

    if not validate_email(email):
        return jsonify(format_error_response('Invalid email format')), 400

    if len(password) < 6:
        return jsonify(format_error_response('Password must be at least 6 characters')), 400

    if not username:
        return jsonify(format_error_response('Username is required')), 400

    try:
        supabase = get_supabase()

        # Check if username exists
        existing = supabase.table(Tables.USERS).select('id').eq('username', username).execute()
        if existing.data:
            return jsonify(format_error_response('Username already taken')), 400

        # Sign up with Supabase Auth
        auth_response = supabase.auth.sign_up({
            'email': email,
            'password': password,
            'options': {
                'data': {
                    'username': username,
                    'full_name': full_name or '',
                    'phone': phone or ''
                }
            }
        })

        if auth_response.user:
            # Create user record in users table
            user_data = {
                'id': auth_response.user.id,
                'email': email,
                'username': username,
                'full_name': full_name or '',
                'phone': phone or ''
            }
            supabase.table(Tables.USERS).insert(user_data).execute()

            # Generate tokens
            access_token = generate_token(auth_response.user.id, 'access')
            refresh_token = generate_token(auth_response.user.id, 'refresh')

            return jsonify(format_success_response({
                'user': user_data,
                'access_token': access_token,
                'refresh_token': refresh_token
            }, 'Registration successful')), 201

    except AuthApiError as e:
        return jsonify(format_error_response(f'Auth error: {str(e)}')), 400
    except Exception as e:
        return jsonify(format_error_response(f'Registration failed: {str(e)}')), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    data = request.get_json()

    if not data:
        return jsonify(format_error_response('No data provided')), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify(format_error_response('Email and password are required')), 400

    try:
        supabase = get_supabase()

        # Sign in with Supabase Auth
        auth_response = supabase.auth.sign_in_with_password({
            'email': email,
            'password': password
        })

        if auth_response.user:
            # Get user data from users table
            user_response = supabase.table(Tables.USERS).select('*').eq('id', auth_response.user.id).single().execute()
            user_data = user_response.data if user_response.data else {
                'id': auth_response.user.id,
                'email': email,
                'username': auth_response.user.user_metadata.get('username', ''),
                'full_name': auth_response.user.user_metadata.get('full_name', ''),
                'phone': auth_response.user.user_metadata.get('phone', '')
            }

            # Generate tokens
            access_token = generate_token(auth_response.user.id, 'access')
            refresh_token = generate_token(auth_response.user.id, 'refresh')

            return jsonify(format_success_response({
                'user': user_data,
                'access_token': access_token,
                'refresh_token': refresh_token
            }, 'Login successful'))

    except AuthApiError as e:
        return jsonify(format_error_response('Invalid email or password')), 401
    except Exception as e:
        return jsonify(format_error_response(f'Login failed: {str(e)}')), 500


@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """Refresh access token"""
    data = request.get_json()
    refresh_token = data.get('refresh_token') if data else None

    if not refresh_token:
        return jsonify(format_error_response('Refresh token is required')), 400

    payload = verify_token(refresh_token)
    if not payload or payload.get('type') != 'refresh':
        return jsonify(format_error_response('Invalid refresh token')), 401

    # Generate new access token
    access_token = generate_token(payload['user_id'], 'access')

    return jsonify(format_success_response({
        'access_token': access_token
    }, 'Token refreshed'))


@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    """Logout user"""
    try:
        supabase = get_supabase()
        supabase.auth.sign_out()
        return jsonify(format_success_response(message='Logout successful'))
    except Exception as e:
        return jsonify(format_error_response(f'Logout error: {str(e)}')), 500


@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user():
    """Get current user info"""
    return jsonify(format_success_response({
        'user': request.current_user
    }))


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset"""
    data = request.get_json()
    email = data.get('email') if data else None

    if not email:
        return jsonify(format_error_response('Email is required')), 400

    try:
        supabase = get_supabase()
        supabase.auth.reset_password_email(email)
        return jsonify(format_success_response(message='Password reset email sent'))
    except Exception as e:
        return jsonify(format_error_response(f'Failed to send reset email: {str(e)}')), 500
