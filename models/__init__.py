"""
Database models and Supabase client initialization
"""
from supabase import create_client, Client
from config import Config

# Supabase client instance
supabase: Client = None


def init_supabase(config: Config):
    """Initialize Supabase client"""
    global supabase
    url = config.get('SUPABASE_URL') if isinstance(config, dict) else config.SUPABASE_URL
key = config.get('SUPABASE_KEY') if isinstance(config, dict) else config.SUPABASE_KEY
if url and key:
    supabase = create_client(url, key)
```

บันทึกแล้วรัน:
```
cd /d D:\forced-learning-app\api
git add models/__init__.py
git commit -m "Fix config access in models"
git push origin main
    return supabase


def get_supabase() -> Client:
    """Get Supabase client instance"""
    if supabase is None:
        raise RuntimeError("Supabase not initialized. Call init_supabase first.")
    return supabase


# Table names for reference
class Tables:
    USERS = 'users'
    COURSES = 'courses'
    USER_COURSES = 'user_courses'
    HWID_BINDINGS = 'hwid_bindings'
    STUDY_PROGRESS = 'study_progress'
    ORDERS = 'orders'
    SYNC_LOGS = 'sync_logs'


# User model helper
class User:
    def __init__(self, data: dict):
        self.id = data.get('id')
        self.email = data.get('email')
        self.username = data.get('username')
        self.full_name = data.get('full_name')
        self.phone = data.get('phone')
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'full_name': self.full_name,
            'phone': self.phone,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


# Course model helper
class Course:
    def __init__(self, data: dict):
        self.id = data.get('id')
        self.name = data.get('name')
        self.description = data.get('description')
        self.price = data.get('price')
        self.slug = data.get('slug')
        self.image_url = data.get('image_url')
        self.is_active = data.get('is_active', True)
        self.flashcard_data_url = data.get('flashcard_data_url')
        self.created_at = data.get('created_at')
        self.updated_at = data.get('updated_at')

    def to_dict(self, include_data_url=False):
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'slug': self.slug,
            'image_url': self.image_url,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
        if include_data_url:
            data['flashcard_data_url'] = self.flashcard_data_url
        return data


# Order model helper
class Order:
    def __init__(self, data: dict):
        self.id = data.get('id')
        self.user_id = data.get('user_id')
        self.course_id = data.get('course_id')
        self.amount = data.get('amount')
        self.currency = data.get('currency', 'THB')
        self.status = data.get('status', 'pending')
        self.payment_method = data.get('payment_method')
        self.payment_proof_url = data.get('payment_proof_url')
        self.paypal_order_id = data.get('paypal_order_id')
        self.paid_at = data.get('paid_at')
        self.created_at = data.get('created_at')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'amount': self.amount,
            'currency': self.currency,
            'status': self.status,
            'payment_method': self.payment_method,
            'payment_proof_url': self.payment_proof_url,
            'paypal_order_id': self.paypal_order_id,
            'paid_at': self.paid_at,
            'created_at': self.created_at
        }


# Study Progress model helper
class StudyProgress:
    def __init__(self, data: dict):
        self.id = data.get('id')
        self.user_id = data.get('user_id')
        self.course_id = data.get('course_id')
        self.card_id = data.get('card_id')
        self.question = data.get('question')
        self.answer = data.get('answer')
        self.study_count = data.get('study_count', 0)
        self.correct_count = data.get('correct_count', 0)
        self.last_studied_at = data.get('last_studied_at')
        self.next_review_at = data.get('next_review_at')
        self.srs_level = data.get('srs_level', 0)
        self.synced_at = data.get('synced_at')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'card_id': self.card_id,
            'question': self.question,
            'answer': self.answer,
            'study_count': self.study_count,
            'correct_count': self.correct_count,
            'last_studied_at': self.last_studied_at,
            'next_review_at': self.next_review_at,
            'srs_level': self.srs_level,
            'synced_at': self.synced_at
        }
