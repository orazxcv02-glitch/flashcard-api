"""
Flashcard E-Learning Platform API
Main Flask Application
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from config import Config
from models import init_supabase
from routes import register_blueprints
import os


def create_app(config_class=Config):
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize CORS
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['*']))

    # Initialize Supabase
    init_supabase(app.config)

    # Register blueprints
    register_blueprints(app)

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'message': 'Endpoint not found'
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'version': '1.0.0',
            'service': 'flashcard-api'
        })

    # Root endpoint
    @app.route('/', methods=['GET'])
    def index():
        return jsonify({
            'name': 'Flashcard E-Learning Platform API',
            'version': '1.0.0',
            'documentation': '/api/health',
            'endpoints': {
                'auth': '/api/auth',
                'courses': '/api/courses',
                'user': '/api/user',
                'orders': '/api/orders',
                'payment': '/api/payment',
                'sync': '/api/sync',
                'admin': '/api/admin'
            }
        })

    return app


# Create app instance
app = create_app()

# For Vercel serverless
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
