"""
Admin Routes
"""
from flask import request, jsonify
from routes import admin_bp
from models import get_supabase, Tables, Course
from utils import token_required, admin_required, format_error_response, format_success_response
from datetime import datetime
import json


@admin_bp.route('/orders', methods=['GET'])
@token_required
def list_orders():
    """List all orders (admin only)"""
    # Check admin (simplified - check for is_admin flag)
    if not request.current_user.get('is_admin', False):
        return jsonify(format_error_response('Admin access required')), 403

    status = request.args.get('status')
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)

    try:
        supabase = get_supabase()

        query = supabase.table(Tables.ORDERS).select('*, courses(*), users(*)').order('created_at', desc=True)

        if status:
            query = query.eq('status', status)

        response = query.limit(limit).offset(offset).execute()

        return jsonify(format_success_response({
            'orders': response.data,
            'count': len(response.data)
        }))

    except Exception as e:
        return jsonify(format_error_response(f'Failed to fetch orders: {str(e)}')), 500


@admin_bp.route('/orders/<order_id>', methods=['PUT'])
@token_required
def update_order(order_id):
    """Update order status (admin only)"""
    if not request.current_user.get('is_admin', False):
        return jsonify(format_error_response('Admin access required')), 403

    data = request.get_json()
    if not data:
        return jsonify(format_error_response('No data provided')), 400

    status = data.get('status')
    if not status:
        return jsonify(format_error_response('Status is required')), 400

    valid_statuses = ['pending', 'paid', 'cancelled', 'refunded']
    if status not in valid_statuses:
        return jsonify(format_error_response(f'Invalid status. Must be one of: {valid_statuses}')), 400

    try:
        supabase = get_supabase()

        # Get order
        order_response = supabase.table(Tables.ORDERS).select('*').eq('id', order_id).single().execute()
        if not order_response.data:
            return jsonify(format_error_response('Order not found')), 404

        order = order_response.data

        update_data = {'status': status}

        if status == 'paid':
            update_data['paid_at'] = datetime.utcnow().isoformat()

            # Grant course access
            existing = supabase.table(Tables.USER_COURSES).select('*').eq(
                'user_id', order['user_id']
            ).eq('course_id', order['course_id']).execute()

            if not existing.data:
                supabase.table(Tables.USER_COURSES).insert({
                    'user_id': order['user_id'],
                    'course_id': order['course_id'],
                    'purchased_at': datetime.utcnow().isoformat()
                }).execute()

        # Update order
        supabase.table(Tables.ORDERS).update(update_data).eq('id', order_id).execute()

        return jsonify(format_success_response(message=f'Order status updated to {status}'))

    except Exception as e:
        return jsonify(format_error_response(f'Update failed: {str(e)}')), 500


@admin_bp.route('/courses', methods=['POST'])
@token_required
def create_course():
    """Create a new course (admin only)"""
    if not request.current_user.get('is_admin', False):
        return jsonify(format_error_response('Admin access required')), 403

    data = request.get_json()
    if not data:
        return jsonify(format_error_response('No data provided')), 400

    required_fields = ['name', 'slug', 'price']
    for field in required_fields:
        if field not in data:
            return jsonify(format_error_response(f'{field} is required')), 400

    try:
        supabase = get_supabase()

        # Check if slug exists
        existing = supabase.table(Tables.COURSES).select('id').eq('slug', data['slug']).execute()
        if existing.data:
            return jsonify(format_error_response('Course slug already exists')), 400

        course_data = {
            'name': data['name'],
            'slug': data['slug'],
            'description': data.get('description', ''),
            'price': data['price'],
            'image_url': data.get('image_url', ''),
            'is_active': data.get('is_active', True),
            'flashcard_data_url': data.get('flashcard_data_url', '')
        }

        response = supabase.table(Tables.COURSES).insert(course_data).execute()
        course = response.data[0] if response.data else None

        return jsonify(format_success_response({
            'course': Course(course).to_dict()
        }, 'Course created')), 201

    except Exception as e:
        return jsonify(format_error_response(f'Failed to create course: {str(e)}')), 500


@admin_bp.route('/courses/<course_id>', methods=['PUT'])
@token_required
def update_course(course_id):
    """Update a course (admin only)"""
    if not request.current_user.get('is_admin', False):
        return jsonify(format_error_response('Admin access required')), 403

    data = request.get_json()
    if not data:
        return jsonify(format_error_response('No data provided')), 400

    allowed_fields = ['name', 'description', 'price', 'image_url', 'is_active', 'flashcard_data_url']
    update_data = {k: v for k, v in data.items() if k in allowed_fields}

    try:
        supabase = get_supabase()

        response = supabase.table(Tables.COURSES).update(update_data).eq('id', course_id).execute()

        if not response.data:
            return jsonify(format_error_response('Course not found')), 404

        return jsonify(format_success_response({
            'course': Course(response.data[0]).to_dict()
        }, 'Course updated'))

    except Exception as e:
        return jsonify(format_error_response(f'Update failed: {str(e)}')), 500


@admin_bp.route('/users', methods=['GET'])
@token_required
def list_users():
    """List all users (admin only)"""
    if not request.current_user.get('is_admin', False):
        return jsonify(format_error_response('Admin access required')), 403

    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)

    try:
        supabase = get_supabase()
        response = supabase.table(Tables.USERS).select('*').limit(limit).offset(offset).execute()

        return jsonify(format_success_response({
            'users': response.data,
            'count': len(response.data)
        }))

    except Exception as e:
        return jsonify(format_error_response(f'Failed to fetch users: {str(e)}')), 500


@admin_bp.route('/stats', methods=['GET'])
@token_required
def get_stats():
    """Get platform statistics (admin only)"""
    if not request.current_user.get('is_admin', False):
        return jsonify(format_error_response('Admin access required')), 403

    try:
        supabase = get_supabase()

        # Count users
        users_count = len(supabase.table(Tables.USERS).select('id', count='exact').execute().data)

        # Count courses
        courses_count = len(supabase.table(Tables.COURSES).select('id', count='exact').execute().data)

        # Count orders by status
        orders_response = supabase.table(Tables.ORDERS).select('status').execute()
        orders_by_status = {}
        total_revenue = 0

        for order in orders_response.data:
            status = order['status']
            orders_by_status[status] = orders_by_status.get(status, 0) + 1
            if status == 'paid':
                total_revenue += float(order.get('amount', 0))

        return jsonify(format_success_response({
            'users_count': users_count,
            'courses_count': courses_count,
            'orders_by_status': orders_by_status,
            'total_revenue': total_revenue
        }))

    except Exception as e:
        return jsonify(format_error_response(f'Failed to fetch stats: {str(e)}')), 500
