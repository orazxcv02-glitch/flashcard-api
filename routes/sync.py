"""
Sync Routes - Study Progress Synchronization
"""
from flask import request, jsonify, current_app
from routes import sync_bp
from models import get_supabase, Tables
from utils import token_required, format_error_response, format_success_response
from datetime import datetime


@sync_bp.route('/progress', methods=['GET'])
@token_required
def get_progress():
    """Get study progress from cloud"""
    user_id = request.current_user['id']
    course_id = request.args.get('course_id')

    try:
        supabase = get_supabase()

        query = supabase.table(Tables.STUDY_PROGRESS).select('*').eq('user_id', user_id)
        if course_id:
            query = query.eq('course_id', course_id)

        response = query.execute()

        progress = []
        for p in response.data:
            progress.append({
                'id': p['id'],
                'course_id': p['course_id'],
                'card_id': p['card_id'],
                'question': p['question'],
                'answer': p['answer'],
                'study_count': p['study_count'],
                'correct_count': p['correct_count'],
                'last_studied_at': p['last_studied_at'],
                'next_review_at': p['next_review_at'],
                'srs_level': p['srs_level'],
                'synced_at': p['synced_at']
            })

        return jsonify(format_success_response({
            'progress': progress,
            'count': len(progress)
        }))

    except Exception as e:
        return jsonify(format_error_response(f'Failed to fetch progress: {str(e)}')), 500


@sync_bp.route('/progress', methods=['POST'])
@token_required
def upload_progress():
    """Upload study progress to cloud"""
    user_id = request.current_user['id']
    data = request.get_json()

    if not data or 'progress' not in data:
        return jsonify(format_error_response('Progress data is required')), 400

    progress_list = data['progress']
    hwid = data.get('hwid', '')

    try:
        supabase = get_supabase()
        now = datetime.utcnow().isoformat()

        inserted_count = 0
        updated_count = 0

        for item in progress_list:
            progress_data = {
                'user_id': user_id,
                'course_id': item.get('course_id'),
                'card_id': item.get('card_id'),
                'question': item.get('question'),
                'answer': item.get('answer'),
                'study_count': item.get('study_count', 0),
                'correct_count': item.get('correct_count', 0),
                'last_studied_at': item.get('last_studied_at'),
                'next_review_at': item.get('next_review_at'),
                'srs_level': item.get('srs_level', 0),
                'synced_at': now
            }

            # Check if progress exists
            existing = supabase.table(Tables.STUDY_PROGRESS).select('id').eq(
                'user_id', user_id
            ).eq('course_id', progress_data['course_id']).eq(
                'card_id', progress_data['card_id']
            ).execute()

            if existing.data:
                # Update existing
                supabase.table(Tables.STUDY_PROGRESS).update(progress_data).eq(
                    'id', existing.data[0]['id']
                ).execute()
                updated_count += 1
            else:
                # Insert new
                supabase.table(Tables.STUDY_PROGRESS).insert(progress_data).execute()
                inserted_count += 1

        # Log sync
        supabase.table(Tables.SYNC_LOGS).insert({
            'user_id': user_id,
            'hwid': hwid,
            'sync_type': 'push',
            'records_count': len(progress_list),
            'synced_at': now,
            'device_info': request.headers.get('User-Agent', '')
        }).execute()

        # Update last sync time for hwid binding
        if hwid:
            supabase.table(Tables.HWID_BINDINGS).update({
                'last_sync_at': now
            }).eq('user_id', user_id).eq('hwid', hwid).execute()

        return jsonify(format_success_response({
            'inserted': inserted_count,
            'updated': updated_count,
            'synced_at': now
        }, 'Progress synced successfully'))

    except Exception as e:
        return jsonify(format_error_response(f'Sync failed: {str(e)}')), 500


@sync_bp.route('/merge', methods=['POST'])
@token_required
def merge_progress():
    """Merge local and cloud progress (conflict resolution)"""
    user_id = request.current_user['id']
    data = request.get_json()

    if not data or 'local_progress' not in data:
        return jsonify(format_error_response('Local progress data is required')), 400

    local_progress = data['local_progress']
    hwid = data.get('hwid', '')

    try:
        supabase = get_supabase()
        now = datetime.utcnow().isoformat()

        # Get cloud progress
        cloud_response = supabase.table(Tables.STUDY_PROGRESS).select('*').eq('user_id', user_id).execute()
        cloud_progress = {p['card_id']: p for p in cloud_response.data}

        merged = []
        conflicts = []

        for local_item in local_progress:
            card_id = local_item.get('card_id')
            course_id = local_item.get('course_id')

            if card_id in cloud_progress:
                cloud_item = cloud_progress[card_id]

                # Compare synced_at timestamps
                local_synced = local_item.get('synced_at', '1970-01-01T00:00:00')
                cloud_synced = cloud_item.get('synced_at', '1970-01-01T00:00:00')

                if local_synced > cloud_synced:
                    # Local is newer, update cloud
                    progress_data = {
                        'user_id': user_id,
                        'course_id': course_id,
                        'card_id': card_id,
                        'question': local_item.get('question'),
                        'answer': local_item.get('answer'),
                        'study_count': local_item.get('study_count', 0),
                        'correct_count': local_item.get('correct_count', 0),
                        'last_studied_at': local_item.get('last_studied_at'),
                        'next_review_at': local_item.get('next_review_at'),
                        'srs_level': local_item.get('srs_level', 0),
                        'synced_at': now
                    }
                    supabase.table(Tables.STUDY_PROGRESS).update(progress_data).eq('id', cloud_item['id']).execute()
                    merged.append({'card_id': card_id, 'resolution': 'local'})
                elif cloud_synced > local_synced:
                    # Cloud is newer, keep cloud
                    conflicts.append({
                        'card_id': card_id,
                        'resolution': 'cloud',
                        'cloud_data': cloud_item
                    })
                else:
                    # Same timestamp, merge stats
                    merged_count = max(local_item.get('study_count', 0), cloud_item.get('study_count', 0))
                    merged_correct = max(local_item.get('correct_count', 0), cloud_item.get('correct_count', 0))

                    progress_data = {
                        'study_count': merged_count,
                        'correct_count': merged_correct,
                        'synced_at': now
                    }
                    supabase.table(Tables.STUDY_PROGRESS).update(progress_data).eq('id', cloud_item['id']).execute()
                    merged.append({'card_id': card_id, 'resolution': 'merged'})
            else:
                # New item from local, insert to cloud
                progress_data = {
                    'user_id': user_id,
                    'course_id': course_id,
                    'card_id': card_id,
                    'question': local_item.get('question'),
                    'answer': local_item.get('answer'),
                    'study_count': local_item.get('study_count', 0),
                    'correct_count': local_item.get('correct_count', 0),
                    'last_studied_at': local_item.get('last_studied_at'),
                    'next_review_at': local_item.get('next_review_at'),
                    'srs_level': local_item.get('srs_level', 0),
                    'synced_at': now
                }
                supabase.table(Tables.STUDY_PROGRESS).insert(progress_data).execute()
                merged.append({'card_id': card_id, 'resolution': 'inserted'})

        # Log sync
        supabase.table(Tables.SYNC_LOGS).insert({
            'user_id': user_id,
            'hwid': hwid,
            'sync_type': 'merge',
            'records_count': len(local_progress),
            'synced_at': now,
            'device_info': request.headers.get('User-Agent', '')
        }).execute()

        return jsonify(format_success_response({
            'merged': merged,
            'conflicts': conflicts,
            'synced_at': now
        }, 'Merge completed'))

    except Exception as e:
        return jsonify(format_error_response(f'Merge failed: {str(e)}')), 500


@sync_bp.route('/logs', methods=['GET'])
@token_required
def get_sync_logs():
    """Get sync logs for user"""
    user_id = request.current_user['id']
    limit = request.args.get('limit', 50, type=int)

    try:
        supabase = get_supabase()
        response = supabase.table(Tables.SYNC_LOGS).select('*').eq('user_id', user_id).order(
            'synced_at', desc=True
        ).limit(limit).execute()

        return jsonify(format_success_response({
            'logs': response.data
        }))

    except Exception as e:
        return jsonify(format_error_response(f'Failed to fetch logs: {str(e)}')), 500
