#!/usr/bin/env python3
"""
Script to manually retry failed tasks from dead letter queue
"""

import sys
import json
import argparse
from pathlib import Path

# Add helpers to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from helpers.queue_manager import get_queue_manager

def list_failed_tasks(queue_name: str):
    """List tasks in dead letter queue"""
    queue_manager = get_queue_manager(queue_name)

    try:
        with queue_manager.db_manager.pool.get_connection() as conn:
            cursor = conn.execute('''
                SELECT id, original_task_id, task_type, task_data,
                       final_error_message, attempt_count, moved_to_dlq_at
                FROM dead_letter_tasks
                WHERE queue_name = ?
                ORDER BY moved_to_dlq_at DESC
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

            return tasks

    except Exception as e:
        print(f"Error listing failed tasks: {e}")
        return []
    finally:
        queue_manager.shutdown()

def retry_task(queue_name: str, task_id: str):
    """Retry a specific task from dead letter queue"""
    queue_manager = get_queue_manager(queue_name)

    try:
        success = queue_manager.retry_dead_letter_task(task_id)

        if success:
            print(f"✓ Task {task_id} has been retried and moved back to queue")
            return True
        else:
            print(f"✗ Failed to retry task {task_id} - task not found or error occurred")
            return False

    except Exception as e:
        print(f"Error retrying task {task_id}: {e}")
        return False
    finally:
        queue_manager.shutdown()

def main():
    parser = argparse.ArgumentParser(description="Retry failed tasks from dead letter queue")
    parser.add_argument("--queue", default="default", help="Queue name")
    parser.add_argument("--list", action="store_true", help="List failed tasks")
    parser.add_argument("--task-id", help="Retry specific task by DLQ ID")
    parser.add_argument("--original-id", help="Retry task by original task ID")
    parser.add_argument("--retry-all", action="store_true", help="Retry all failed tasks")

    args = parser.parse_args()

    if args.list:
        print(f"Failed tasks in queue '{args.queue}':")
        print("=" * 60)

        tasks = list_failed_tasks(args.queue)

        if not tasks:
            print("No failed tasks found.")
            return

        for task in tasks:
            print(f"DLQ ID: {task['dlq_id']}")
            print(f"Original ID: {task['original_task_id']}")
            print(f"Task Type: {task['task_type']}")
            print(f"Attempts: {task['attempt_count']}")
            print(f"Error: {task['final_error_message']}")
            print(f"Failed At: {task['moved_to_dlq_at']}")
            print(f"Data: {json.dumps(task['task_data'], indent=2)}")
            print("-" * 60)

    elif args.task_id:
        print(f"Retrying task {args.task_id} from queue '{args.queue}'...")
        success = retry_task(args.queue, args.task_id)
        sys.exit(0 if success else 1)

    elif args.original_id:
        # Find DLQ ID by original task ID
        tasks = list_failed_tasks(args.queue)
        dlq_id = None

        for task in tasks:
            if task['original_task_id'] == args.original_id:
                dlq_id = task['dlq_id']
                break

        if dlq_id:
            print(f"Found task {args.original_id} in DLQ with ID {dlq_id}")
            print(f"Retrying...")
            success = retry_task(args.queue, dlq_id)
            sys.exit(0 if success else 1)
        else:
            print(f"Task with original ID {args.original_id} not found in dead letter queue")
            sys.exit(1)

    elif args.retry_all:
        print(f"Retrying all failed tasks in queue '{args.queue}'...")

        tasks = list_failed_tasks(args.queue)

        if not tasks:
            print("No failed tasks to retry.")
            return

        success_count = 0
        for task in tasks:
            print(f"Retrying task {task['dlq_id']} (original: {task['original_task_id']})...")
            if retry_task(args.queue, task['dlq_id']):
                success_count += 1

        print(f"Successfully retried {success_count}/{len(tasks)} tasks")

        if success_count < len(tasks):
            sys.exit(1)

    else:
        print("Please specify --list, --task-id, --original-id, or --retry-all")
        print("Use --help for more information")
        sys.exit(1)

if __name__ == "__main__":
    main()