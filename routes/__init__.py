"""
API Routes Blueprint Registration
"""
from flask import Blueprint

# Create blueprints
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
courses_bp = Blueprint('courses', __name__, url_prefix='/api/courses')
orders_bp = Blueprint('orders', __name__, url_prefix='/api/orders')
payment_bp = Blueprint('payment', __name__, url_prefix='/api/payment')
sync_bp = Blueprint('sync', __name__, url_prefix='/api/sync')
user_bp = Blueprint('user', __name__, url_prefix='/api/user')
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# Import route handlers
from . import auth
from . import courses
from . import orders
from . import payment
from . import sync
from . import user
from . import admin


def register_blueprints(app):
    """Register all blueprints with the Flask app"""
    app.register_blueprint(auth_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(sync_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
