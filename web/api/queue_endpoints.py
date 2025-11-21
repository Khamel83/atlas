#!/usr/bin/env python3
"""
Queue status API endpoints
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, request
import logging

# Add helpers to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from helpers.queue_manager import get_queue_manager

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

@app.route('/api/v1/queue/status', methods=['GET'])
def get_queue_status():
    """Get overall queue status"""
    try:
        queue_name = request.args.get('queue', 'default')
        queue_manager = get_queue_manager(queue_name)

        stats = queue_manager.get_queue_stats()

        # Add additional status information
        status = {
            'queue_name': queue_name,
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy' if not stats.get('error') else 'error',
            'statistics': stats
        }

        # Check for alerts
        alerts = []

        # Alert if queue depth > 1000
        pending_count = stats.get('tasks_pending', 0)
        if pending_count > 1000:
            alerts.append({
                'level': 'warning',
                'message': f'High queue depth: {pending_count} pending tasks'
            })

        # Alert if dead letter queue has items
        dlq_count = stats.get('tasks_in_dlq', 0)
        if dlq_count > 0:
            alerts.append({
                'level': 'warning',
                'message': f'Dead letter queue has {dlq_count} failed tasks'
            })

        # Alert if circuit breaker is open
        cb_status = stats.get('circuit_breaker', {})
        if cb_status.get('state') == 'open':
            alerts.append({
                'level': 'critical',
                'message': 'Circuit breaker is open - queue processing disabled'
            })

        status['alerts'] = alerts

        return jsonify(status)

    except Exception as e:
        app.logger.error(f"Error getting queue status: {e}")
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/v1/queue/<queue_name>/stats', methods=['GET'])
def get_specific_queue_stats(queue_name):
    """Get stats for a specific queue"""
    try:
        queue_manager = get_queue_manager(queue_name)
        stats = queue_manager.get_queue_stats()

        return jsonify({
            'queue_name': queue_name,
            'timestamp': datetime.now().isoformat(),
            'statistics': stats
        })

    except Exception as e:
        app.logger.error(f"Error getting stats for queue {queue_name}: {e}")
        return jsonify({
            'error': str(e),
            'queue_name': queue_name,
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/v1/queue/<queue_name>/circuit-breaker', methods=['GET'])
def get_circuit_breaker_status(queue_name):
    """Get circuit breaker status for queue"""
    try:
        queue_manager = get_queue_manager(queue_name)
        status = queue_manager.circuit_breaker.get_status()

        return jsonify({
            'queue_name': queue_name,
            'timestamp': datetime.now().isoformat(),
            'circuit_breaker': status
        })

    except Exception as e:
        app.logger.error(f"Error getting circuit breaker status for queue {queue_name}: {e}")
        return jsonify({
            'error': str(e),
            'queue_name': queue_name,
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/v1/queue/<queue_name>/circuit-breaker/reset', methods=['POST'])
def reset_circuit_breaker(queue_name):
    """Reset circuit breaker for queue"""
    try:
        queue_manager = get_queue_manager(queue_name)

        # Reset circuit breaker
        with queue_manager.circuit_breaker.lock:
            queue_manager.circuit_breaker.state = queue_manager.circuit_breaker.CircuitBreakerState.CLOSED
            queue_manager.circuit_breaker.failure_count = 0
            queue_manager.circuit_breaker.last_failure_time = None
            queue_manager.circuit_breaker.consecutive_successes = 0

        app.logger.info(f"Circuit breaker reset for queue {queue_name}")

        return jsonify({
            'message': f'Circuit breaker reset for queue {queue_name}',
            'queue_name': queue_name,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        app.logger.error(f"Error resetting circuit breaker for queue {queue_name}: {e}")
        return jsonify({
            'error': str(e),
            'queue_name': queue_name,
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/v1/queue/<queue_name>/tasks', methods=['POST'])
def enqueue_task(queue_name):
    """Enqueue a new task"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        task_type = data.get('task_type')
        task_data = data.get('task_data', {})
        max_attempts = data.get('max_attempts', 9)

        if not task_type:
            return jsonify({'error': 'task_type is required'}), 400

        queue_manager = get_queue_manager(queue_name)
        task_id = queue_manager.enqueue(task_type, task_data, max_attempts)

        return jsonify({
            'task_id': task_id,
            'queue_name': queue_name,
            'message': 'Task enqueued successfully',
            'timestamp': datetime.now().isoformat()
        }), 201

    except Exception as e:
        app.logger.error(f"Error enqueuing task to queue {queue_name}: {e}")
        return jsonify({
            'error': str(e),
            'queue_name': queue_name,
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/v1/queue/<queue_name>/dead-letter', methods=['GET'])
def get_dead_letter_tasks(queue_name):
    """Get dead letter queue tasks"""
    try:
        queue_manager = get_queue_manager(queue_name)

        with queue_manager.db_manager.pool.get_connection() as conn:
            cursor = conn.execute('''
                SELECT id, original_task_id, task_type, task_data,
                       final_error_message, attempt_count, moved_to_dlq_at
                FROM dead_letter_tasks
                WHERE queue_name = ?
                ORDER BY moved_to_dlq_at DESC
                LIMIT 100
            ''', (queue_name,))

            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    'dlq_id': row[0],
                    'original_task_id': row[1],
                    'task_type': row[2],
                    'task_data': json.loads(row[3]),
                    'final_error_message': row[4],
                    'attempt_count': row[5],
                    'moved_to_dlq_at': row[6]
                })

        return jsonify({
            'queue_name': queue_name,
            'dead_letter_tasks': tasks,
            'count': len(tasks),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        app.logger.error(f"Error getting dead letter tasks for queue {queue_name}: {e}")
        return jsonify({
            'error': str(e),
            'queue_name': queue_name,
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/v1/queue/<queue_name>/dead-letter/<dlq_task_id>/retry', methods=['POST'])
def retry_dead_letter_task(queue_name, dlq_task_id):
    """Retry a task from dead letter queue"""
    try:
        queue_manager = get_queue_manager(queue_name)
        success = queue_manager.retry_dead_letter_task(dlq_task_id)

        if success:
            return jsonify({
                'message': f'Dead letter task {dlq_task_id} retried successfully',
                'dlq_task_id': dlq_task_id,
                'queue_name': queue_name,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'error': f'Failed to retry dead letter task {dlq_task_id}',
                'dlq_task_id': dlq_task_id,
                'queue_name': queue_name,
                'timestamp': datetime.now().isoformat()
            }), 404

    except Exception as e:
        app.logger.error(f"Error retrying dead letter task {dlq_task_id}: {e}")
        return jsonify({
            'error': str(e),
            'dlq_task_id': dlq_task_id,
            'queue_name': queue_name,
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """API health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'queue-api',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    # Development server
    app.run(host='0.0.0.0', port=7444, debug=True)