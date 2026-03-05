"""
Order Routes
"""
from flask import request, jsonify
from routes import orders_bp
from models import get_supabase, Tables, Order
from utils import token_required, admin_required, format_error_response, format_success_response
from datetime import datetime


@orders_bp.route('/', methods=['POST'])
@token_required
def create_order():
    """Create a new order"""
    data = request.get_json()
    user_id = request.current_user['id']

    course_id = data.get('course_id') if data else None
    amount = data.get('amount') if data else None
    currency = data.get('currency', 'THB')

    if not course_id or not amount:
        return jsonify(format_error_response('Course ID and amount are required')), 400

    try:
        supabase = get_supabase()

        # Verify course exists and get price
        course_response = supabase.table(Tables.COURSES).select('*').eq('id', course_id).single().execute()
        if not course_response.data:
            return jsonify(format_error_response('Course not found')), 404

        course = course_response.data

        # Check if user already owns the course
        existing = supabase.table(Tables.USER_COURSES).select('*').eq('user_id', user_id).eq('course_id', course_id).eq('is_active', True).execute()
        if existing.data:
            return jsonify(format_error_response('You already own this course')), 400

        # Create order
        order_data = {
            'user_id': user_id,
            'course_id': course_id,
            'amount': amount,
            'currency': currency,
            'status': 'pending'
        }

        response = supabase.table(Tables.ORDERS).insert(order_data).execute()
        order = response.data[0] if response.data else None

        return jsonify(format_success_response({
            'order': Order(order).to_dict()
        }, 'Order created')), 201

    except Exception as e:
        return jsonify(format_error_response(f'Failed to create order: {str(e)}')), 500


@orders_bp.route('/<order_id>', methods=['GET'])
@token_required
def get_order(order_id):
    """Get order details"""
    user_id = request.current_user['id']

    try:
        supabase = get_supabase()
        response = supabase.table(Tables.ORDERS).select('*, courses(*)').eq('id', order_id).single().execute()

        if not response.data:
            return jsonify(format_error_response('Order not found')), 404

        order = response.data

        # Verify ownership (unless admin)
        if order['user_id'] != user_id and not request.current_user.get('is_admin'):
            return jsonify(format_error_response('Access denied')), 403

        return jsonify(format_success_response({
            'order': {
                **Order(order).to_dict(),
                'course': order.get('courses', {})
            }
        }))

    except Exception as e:
        return jsonify(format_error_response(f'Failed to fetch order: {str(e)}')), 500


@orders_bp.route('/my-orders', methods=['GET'])
@token_required
def get_my_orders():
    """Get user's orders"""
    user_id = request.current_user['id']

    try:
        supabase = get_supabase()
        response = supabase.table(Tables.ORDERS).select('*, courses(*)').eq('user_id', user_id).order('created_at', desc=True).execute()

        orders = []
        for o in response.data:
            orders.append({
                **Order(o).to_dict(),
                'course': o.get('courses', {})
            })

        return jsonify(format_success_response({'orders': orders}))

    except Exception as e:
        return jsonify(format_error_response(f'Failed to fetch orders: {str(e)}')), 500


@orders_bp.route('/<order_id>/upload-slip', methods=['POST'])
@token_required
def upload_slip(order_id):
    """Upload bank transfer slip"""
    user_id = request.current_user['id']

    if 'slip' not in request.files:
        return jsonify(format_error_response('Slip image is required')), 400

    file = request.files['slip']
    if file.filename == '':
        return jsonify(format_error_response('No file selected')), 400

    try:
        supabase = get_supabase()

        # Verify order ownership
        order_response = supabase.table(Tables.ORDERS).select('*').eq('id', order_id).single().execute()
        if not order_response.data:
            return jsonify(format_error_response('Order not found')), 404

        order = order_response.data
        if order['user_id'] != user_id:
            return jsonify(format_error_response('Access denied')), 403

        if order['status'] != 'pending':
            return jsonify(format_error_response('Order already processed')), 400

        # Upload to Supabase Storage
        file_path = f"payment_slips/{order_id}_{file.filename}"
        supabase.storage.from_('payments').upload(file_path, file.read())

        # Get public URL
        slip_url = supabase.storage.from_('payments').get_public_url(file_path)

        # Update order
        supabase.table(Tables.ORDERS).update({
            'payment_method': 'bank_transfer',
            'payment_proof_url': slip_url
        }).eq('id', order_id).execute()

        return jsonify(format_success_response({
            'slip_url': slip_url
        }, 'Slip uploaded successfully'))

    except Exception as e:
        return jsonify(format_error_response(f'Upload failed: {str(e)}')), 500
