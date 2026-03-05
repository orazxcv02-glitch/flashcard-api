"""
Payment Routes - PayPal Integration
"""
from flask import request, jsonify, current_app
from routes import payment_bp
from models import get_supabase, Tables
from utils import token_required, format_error_response, format_success_response
from datetime import datetime
import paypalrestsdk


def get_paypal_api():
    """Initialize PayPal API"""
    mode = current_app.config.get('PAYPAL_MODE', 'sandbox')
    client_id = current_app.config.get('PAYPAL_CLIENT_ID')
    client_secret = current_app.config.get('PAYPAL_SECRET')

    if not client_id or not client_secret:
        raise ValueError("PayPal credentials not configured")

    paypalrestsdk.configure({
        "mode": mode,
        "client_id": client_id,
        "client_secret": client_secret
    })

    return paypalrestsdk


@payment_bp.route('/paypal/create/<order_id>', methods=['POST'])
@token_required
def create_paypal_payment(order_id):
    """Create PayPal payment"""
    user_id = request.current_user['id']

    try:
        supabase = get_supabase()
        paypal = get_paypal_api()

        # Get order details
        order_response = supabase.table(Tables.ORDERS).select('*, courses(*)').eq('id', order_id).single().execute()
        if not order_response.data:
            return jsonify(format_error_response('Order not found')), 404

        order = order_response.data

        # Verify ownership
        if order['user_id'] != user_id:
            return jsonify(format_error_response('Access denied')), 403

        if order['status'] != 'pending':
            return jsonify(format_error_response('Order already processed')), 400

        course = order.get('courses', {})

        # Create PayPal payment
        payment = paypal.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": f"{current_app.config['FRONTEND_URL']}/payment/success",
                "cancel_url": f"{current_app.config['FRONTEND_URL']}/payment/cancel"
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": course.get('name', 'Course'),
                        "sku": course.get('slug', 'course'),
                        "price": str(order['amount']),
                        "currency": order.get('currency', 'THB'),
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": str(order['amount']),
                    "currency": order.get('currency', 'THB')
                },
                "description": f"Purchase of {course.get('name', 'Course')}"
            }]
        })

        if payment.create():
            # Update order with PayPal payment ID
            supabase.table(Tables.ORDERS).update({
                'paypal_order_id': payment.id,
                'payment_method': 'paypal'
            }).eq('id', order_id).execute()

            # Find approval URL
            approval_url = None
            for link in payment.links:
                if link.method == "REDIRECT" and link.rel == "approval_url":
                    approval_url = link.href
                    break

            return jsonify(format_success_response({
                'payment_id': payment.id,
                'approval_url': approval_url
            }))
        else:
            return jsonify(format_error_response(payment.error)), 500

    except Exception as e:
        return jsonify(format_error_response(f'Payment creation failed: {str(e)}')), 500


@payment_bp.route('/paypal/execute/<order_id>', methods=['POST'])
@token_required
def execute_paypal_payment(order_id):
    """Execute PayPal payment after approval"""
    user_id = request.current_user['id']
    data = request.get_json()
    payment_id = data.get('payment_id') if data else None
    payer_id = data.get('payer_id') if data else None

    if not payment_id or not payer_id:
        return jsonify(format_error_response('Payment ID and Payer ID are required')), 400

    try:
        supabase = get_supabase()
        paypal = get_paypal_api()

        # Get order
        order_response = supabase.table(Tables.ORDERS).select('*').eq('id', order_id).single().execute()
        if not order_response.data:
            return jsonify(format_error_response('Order not found')), 404

        order = order_response.data

        # Verify ownership
        if order['user_id'] != user_id:
            return jsonify(format_error_response('Access denied')), 403

        # Execute payment
        payment = paypal.Payment.find(payment_id)

        if payment.execute({"payer_id": payer_id}):
            # Update order status
            now = datetime.utcnow().isoformat()
            supabase.table(Tables.ORDERS).update({
                'status': 'paid',
                'paid_at': now
            }).eq('id', order_id).execute()

            # Grant course access
            supabase.table(Tables.USER_COURSES).insert({
                'user_id': user_id,
                'course_id': order['course_id'],
                'purchased_at': now
            }).execute()

            return jsonify(format_success_response(message='Payment successful'))
        else:
            return jsonify(format_error_response(payment.error)), 500

    except Exception as e:
        return jsonify(format_error_response(f'Payment execution failed: {str(e)}')), 500


@payment_bp.route('/paypal/webhook', methods=['POST'])
def paypal_webhook():
    """Handle PayPal webhooks"""
    data = request.get_json()

    # Verify webhook (PayPal webhook verification)
    # This is a simplified version - implement full verification in production
    event_type = data.get('event_type')

    if event_type == 'PAYMENT.CAPTURE.COMPLETED':
        resource = data.get('resource', {})
        payment_id = resource.get('id')

        try:
            supabase = get_supabase()

            # Find order by PayPal payment ID
            order_response = supabase.table(Tables.ORDERS).select('*').eq('paypal_order_id', payment_id).execute()

            if order_response.data:
                order = order_response.data[0]
                now = datetime.utcnow().isoformat()

                # Update order
                supabase.table(Tables.ORDERS).update({
                    'status': 'paid',
                    'paid_at': now
                }).eq('id', order['id']).execute()

                # Grant access if not already granted
                existing = supabase.table(Tables.USER_COURSES).select('*').eq('user_id', order['user_id']).eq('course_id', order['course_id']).execute()
                if not existing.data:
                    supabase.table(Tables.USER_COURSES).insert({
                        'user_id': order['user_id'],
                        'course_id': order['course_id'],
                        'purchased_at': now
                    }).execute()

            return jsonify({'success': True}), 200

        except Exception as e:
            return jsonify(format_error_response(f'Webhook processing failed: {str(e)}')), 500

    return jsonify({'success': True}), 200
