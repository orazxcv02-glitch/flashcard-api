"""
Utility functions and decorators
"""
from functools import wraps
from flask import request, jsonify, current_app
import jwt
import hmac
import hashlib
from datetime import datetime, timedelta
from models import get_supabase, Tables


def generate_token(user_id: str, token_type: str = 'access') -> str:
    """Generate JWT token"""
    if token_type == 'access':
        expires = datetime.utcnow() + timedelta(seconds=current_app.config['JWT_ACCESS_TOKEN_EXPIRES'])
    else:
        expires = datetime.utcnow() + timedelta(seconds=current_app.config['JWT_REFRESH_TOKEN_EXPIRES'])

    payload = {
        'user_id': user_id,
        'type': token_type,
        'exp': expires,
        'iat': datetime.utcnow()
    }

    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')


def verify_token(token: str) -> dict:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    """Decorator to protect routes with JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')

        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'success': False, 'message': 'Token is missing'}), 401

        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'message': 'Token is invalid or expired'}), 401

        # Get current user from Supabase
        try:
            supabase = get_supabase()
            user_response = supabase.table(Tables.USERS).select('*').eq('id', payload['user_id']).single().execute()
            if not user_response.data:
                return jsonify({'success': False, 'message': 'User not found'}), 401

            request.current_user = user_response.data
        except Exception as e:
            return jsonify({'success': False, 'message': f'Error fetching user: {str(e)}'}), 500

        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        # Check if user has admin role
        user = request.current_user
        if not user.get('is_admin', False):
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        return f(*args, **kwargs)

    return decorated


def verify_data_signature(data: dict, signature: str, secret: bytes) -> bool:
    """Verify HMAC signature of data"""
    if 'sig' in data:
        data_copy = {k: v for k, v in data.items() if k != 'sig'}
    else:
        data_copy = data

    payload_str = str(data_copy)  # Simple string representation for verification
    expected_sig = hmac.new(secret, payload_str.encode('utf-8'), hashlib.sha256).hexdigest()

    return hmac.compare_digest(expected_sig, signature)


def generate_data_signature(data: dict, secret: bytes) -> str:
    """Generate HMAC signature for data"""
    payload_str = str(data)
    return hmac.new(secret, payload_str.encode('utf-8'), hashlib.sha256).hexdigest()


def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_phone(phone: str) -> bool:
    """Basic Thai phone validation"""
    import re
    pattern = r'^(0[689]\d{8}|\+66[689]\d{8})$'
    return re.match(pattern, phone) is not None


def format_error_response(message: str, errors: dict = None) -> dict:
    """Format error response"""
    response = {'success': False, 'message': message}
    if errors:
        response['errors'] = errors
    return response


def format_success_response(data: dict = None, message: str = None) -> dict:
    """Format success response"""
    response = {'success': True}
    if data:
        response['data'] = data
    if message:
        response['message'] = message
    return response
