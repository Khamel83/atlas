#!/usr/bin/env python3
"""
Learning & Improvement System

Continuous learning from usage patterns to improve command generation,
workflow execution, and system performance.
"""

import json
import sqlite3
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import logging
from collections import defaultdict, Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle


@dataclass
class UsagePattern:
    """Represents a usage pattern from command execution"""
    pattern_id: str
    pattern_type: str  # 'command_sequence', 'parameter_choice', 'workflow_usage'
    pattern_data: Dict[str, Any]
    frequency: int
    success_rate: float
    last_used: datetime
    context: Dict[str, Any]


@dataclass
class LearningData:
    """Learning data point from system usage"""
    timestamp: datetime
    user_id: Optional[str]
    session_id: str
    command_name: str
    parameters: Dict[str, Any]
    execution_time: float
    success: bool
    error_message: Optional[str]
    context: Dict[str, Any]


@dataclass
class ImprovementSuggestion:
    """Suggestion for system improvement"""
    suggestion_id: str
    suggestion_type: str  # 'command', 'workflow', 'parameter', 'performance'
    description: str
    confidence: float
    data: Dict[str, Any]
    created_at: datetime
    implemented: bool = False


class LearningSystem:
    """Main learning system class"""

    def __init__(self, db_path: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        self.config = {**self._default_config(), **(config or {})}
        self.db_path = db_path or str(Path.home() / ".oos" / "learning.db")
        self.logger = self._setup_logger()

        # Initialize database
        self._init_database()

        # Pattern detection models
        self.command_sequence_model = TfidfVectorizer(max_features=1000)
        self.parameter_patterns = defaultdict(Counter)
        self.workflow_usage = defaultdict(Counter)

        # Learning state
        self.patterns = []
        self.suggestions = []
        self.last_learning_update = datetime.now()

    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for learning system"""
        return {
            "learning_enabled": True,
            "pattern_detection_threshold": 0.7,
            "min_pattern_frequency": 3,
            "learning_interval_hours": 24,
            "max_suggestions": 100,
            "retention_days": 90,
            "confidence_threshold": 0.8
        }

    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the learning system"""
        logger = logging.getLogger('learning_system')
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _init_database(self):
        """Initialize SQLite database for learning data"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS learning_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id TEXT,
                    session_id TEXT NOT NULL,
                    command_name TEXT NOT NULL,
                    parameters TEXT,
                    execution_time REAL,
                    success BOOLEAN,
                    error_message TEXT,
                    context TEXT
                )
            ''')

            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_learning_data_command_name ON learning_data(command_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_learning_data_timestamp ON learning_data(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_learning_data_success ON learning_data(success)')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS patterns (
                    pattern_id TEXT PRIMARY KEY,
                    pattern_type TEXT NOT NULL,
                    pattern_data TEXT NOT NULL,
                    frequency INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.0,
                    last_used TEXT,
                    context TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS suggestions (
                    suggestion_id TEXT PRIMARY KEY,
                    suggestion_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    confidence REAL,
                    data TEXT,
                    created_at TEXT,
                    implemented BOOLEAN DEFAULT FALSE
                )
            ''')

            conn.commit()

    def record_usage(self, learning_data: LearningData):
        """Record usage data for learning"""
        if not self.config["learning_enabled"]:
            return

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO learning_data
                    (timestamp, user_id, session_id, command_name, parameters,
                     execution_time, success, error_message, context)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    learning_data.timestamp.isoformat(),
                    learning_data.user_id,
                    learning_data.session_id,
                    learning_data.command_name,
                    json.dumps(learning_data.parameters),
                    learning_data.execution_time,
                    learning_data.success,
                    learning_data.error_message,
                    json.dumps(learning_data.context)
                ))

                conn.commit()

        except Exception as e:
            self.logger.error(f"Failed to record usage data: {e}")

    async def learn_patterns(self) -> List[UsagePattern]:
        """Learn patterns from usage data"""
        if not self.config["learning_enabled"]:
            return []

        # Check if it's time to learn
        if (datetime.now() - self.last_learning_update).total_seconds() < \
           self.config["learning_interval_hours"] * 3600:
            return self.patterns

        try:
            # Get recent usage data
            cutoff_date = datetime.now() - timedelta(days=self.config["retention_days"])

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT * FROM learning_data
                    WHERE timestamp > ?
                    ORDER BY timestamp
                ''', (cutoff_date.isoformat(),))

                usage_data = cursor.fetchall()

            if not usage_data:
                return []

            # Learn command sequences
            command_sequences = self._learn_command_sequences(usage_data)

            # Learn parameter patterns
            parameter_patterns = self._learn_parameter_patterns(usage_data)

            # Learn workflow patterns
            workflow_patterns = self._learn_workflow_patterns(usage_data)

            # Combine all patterns
            all_patterns = command_sequences + parameter_patterns + workflow_patterns

            # Filter by frequency threshold
            filtered_patterns = [
                p for p in all_patterns
                if p.frequency >= self.config["min_pattern_frequency"]
            ]

            # Save patterns
            self._save_patterns(filtered_patterns)
            self.patterns = filtered_patterns

            # Update last learning time
            self.last_learning_update = datetime.now()

            self.logger.info(f"Learned {len(filtered_patterns)} patterns from {len(usage_data)} usage records")

            return filtered_patterns

        except Exception as e:
            self.logger.error(f"Failed to learn patterns: {e}")
            return []

    def _learn_command_sequences(self, usage_data: List) -> List[UsagePattern]:
        """Learn command sequences from usage data"""
        sequences = defaultdict(list)
        pattern_id = 0

        # Group by session to get sequences
        session_commands = defaultdict(list)
        for record in usage_data:
            session_commands[record[3]].append({  # session_id is index 3
                'command': record[4],  # command_name
                'success': record[7],  # success
                'timestamp': record[1]  # timestamp
            })

        # Find sequences
        for session_id, commands in session_commands.items():
            if len(commands) < 2:
                continue

            # Sort by timestamp
            commands.sort(key=lambda x: x['timestamp'])

            # Extract sequences of 2-5 commands
            for seq_len in range(2, min(6, len(commands) + 1)):
                for i in range(len(commands) - seq_len + 1):
                    sequence = commands[i:i + seq_len]

                    # Only consider successful sequences
                    if all(cmd['success'] for cmd in sequence):
                        sequence_key = ' -> '.join(cmd['command'] for cmd in sequence)
                        sequences[sequence_key].append(sequence)

        # Create pattern objects
        patterns = []
        for sequence_key, occurrences in sequences.items():
            if len(occurrences) >= self.config["min_pattern_frequency"]:
                success_count = sum(1 for seq in occurrences if all(cmd['success'] for cmd in seq))
                success_rate = success_count / len(occurrences)

                pattern = UsagePattern(
                    pattern_id=f"seq_{pattern_id}",
                    pattern_type="command_sequence",
                    pattern_data={
                        "sequence": [cmd['command'] for cmd in occurrences[0]],
                        "length": len(occurrences[0])
                    },
                    frequency=len(occurrences),
                    success_rate=success_rate,
                    last_used=datetime.now(),
                    context={"session_count": len(set(seq[3] for seq in usage_data))}
                )
                patterns.append(pattern)
                pattern_id += 1

        return patterns

    def _learn_parameter_patterns(self, usage_data: List) -> List[UsagePattern]:
        """Learn parameter usage patterns"""
        patterns = []
        pattern_id = 0

        # Group by command and parameter
        param_usage = defaultdict(lambda: defaultdict(Counter))

        for record in usage_data:
            command = record[4]  # command_name
            parameters = json.loads(record[5]) if record[5] else {}  # parameters
            success = record[7]  # success

            for param_name, param_value in parameters.items():
                param_usage[command][param_name][str(param_value)] += 1 if success else 0

        # Create parameter patterns
        for command, params in param_usage.items():
            for param_name, values in params.items():
                if sum(values.values()) >= self.config["min_pattern_frequency"]:
                    most_common = values.most_common(1)[0]

                    pattern = UsagePattern(
                        pattern_id=f"param_{pattern_id}",
                        pattern_type="parameter_choice",
                        pattern_data={
                            "command": command,
                            "parameter": param_name,
                            "common_value": most_common[0],
                            "usage_count": most_common[1]
                        },
                        frequency=sum(values.values()),
                        success_rate=most_common[1] / sum(values.values()),
                        last_used=datetime.now(),
                        context={"total_options": len(values)}
                    )
                    patterns.append(pattern)
                    pattern_id += 1

        return patterns

    def _learn_workflow_patterns(self, usage_data: List) -> List[UsagePattern]:
        """Learn workflow usage patterns"""
        patterns = []
        pattern_id = 0

        # Group workflows by execution patterns
        workflow_executions = defaultdict(list)

        for record in usage_data:
            if record[4] == "execute-workflow":  # command_name
                parameters = json.loads(record[5]) if record[5] else {}
                workflow_id = parameters.get("workflow_id")
                if workflow_id:
                    workflow_executions[workflow_id].append({
                        "success": record[7],
                        "execution_time": record[6],
                        "timestamp": record[1]
                    })

        # Analyze workflow patterns
        for workflow_id, executions in workflow_executions.items():
            if len(executions) >= self.config["min_pattern_frequency"]:
                success_count = sum(1 for ex in executions if ex["success"])
                avg_execution_time = np.mean([ex["execution_time"] for ex in executions])

                pattern = UsagePattern(
                    pattern_id=f"workflow_{pattern_id}",
                    pattern_type="workflow_usage",
                    pattern_data={
                        "workflow_id": workflow_id,
                        "avg_execution_time": avg_execution_time,
                        "success_rate": success_count / len(executions)
                    },
                    frequency=len(executions),
                    success_rate=success_count / len(executions),
                    last_used=datetime.now(),
                    context={"total_executions": len(executions)}
                )
                patterns.append(pattern)
                pattern_id += 1

        return patterns

    def _save_patterns(self, patterns: List[UsagePattern]):
        """Save learned patterns to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for pattern in patterns:
                cursor.execute('''
                    INSERT OR REPLACE INTO patterns
                    (pattern_id, pattern_type, pattern_data, frequency, success_rate, last_used, context)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    pattern.pattern_id,
                    pattern.pattern_type,
                    json.dumps(pattern.pattern_data),
                    pattern.frequency,
                    pattern.success_rate,
                    pattern.last_used.isoformat(),
                    json.dumps(pattern.context)
                ))

            conn.commit()

    async def generate_suggestions(self) -> List[ImprovementSuggestion]:
        """Generate improvement suggestions based on patterns"""
        suggestions = []

        # Analyze patterns for improvement opportunities
        if not self.patterns:
            await self.learn_patterns()

        # Generate command suggestions
        command_suggestions = self._generate_command_suggestions()
        suggestions.extend(command_suggestions)

        # Generate workflow suggestions
        workflow_suggestions = self._generate_workflow_suggestions()
        suggestions.extend(workflow_suggestions)

        # Generate parameter suggestions
        parameter_suggestions = self._generate_parameter_suggestions()
        suggestions.extend(parameter_suggestions)

        # Filter by confidence
        filtered_suggestions = [
            s for s in suggestions
            if s.confidence >= self.config["confidence_threshold"]
        ]

        # Save suggestions
        self._save_suggestions(filtered_suggestions)
        self.suggestions = filtered_suggestions

        return filtered_suggestions

    def _generate_command_suggestions(self) -> List[ImprovementSuggestion]:
        """Generate suggestions for command improvements"""
        suggestions = []

        # Analyze command sequences for new workflow opportunities
        sequence_patterns = [p for p in self.patterns if p.pattern_type == "command_sequence"]

        for pattern in sequence_patterns:
            if pattern.frequency >= 5 and pattern.success_rate >= 0.8:
                suggestion = ImprovementSuggestion(
                    suggestion_id=f"cmd_workflow_{pattern.pattern_id}",
                    suggestion_type="workflow",
                    description=f"Create workflow for common sequence: {' -> '.join(pattern.pattern_data['sequence'])}",
                    confidence=min(0.9, pattern.frequency / 10),
                    data={
                        "sequence": pattern.pattern_data["sequence"],
                        "frequency": pattern.frequency,
                        "success_rate": pattern.success_rate
                    },
                    created_at=datetime.now()
                )
                suggestions.append(suggestion)

        return suggestions

    def _generate_workflow_suggestions(self) -> List[ImprovementSuggestion]:
        """Generate suggestions for workflow improvements"""
        suggestions = []

        # Analyze workflow performance
        workflow_patterns = [p for p in self.patterns if p.pattern_type == "workflow_usage"]

        for pattern in workflow_patterns:
            # Suggest optimization for slow workflows
            if pattern.pattern_data["avg_execution_time"] > 300:  # 5 minutes
                suggestion = ImprovementSuggestion(
                    suggestion_id=f"workflow_perf_{pattern.pattern_id}",
                    suggestion_type="performance",
                    description=f"Optimize slow workflow: {pattern.pattern_data['workflow_id']} "
                               f"(avg: {pattern.pattern_data['avg_execution_time']:.1f}s)",
                    confidence=0.8,
                    data={
                        "workflow_id": pattern.pattern_data["workflow_id"],
                        "avg_execution_time": pattern.pattern_data["avg_execution_time"],
                        "current_success_rate": pattern.success_rate
                    },
                    created_at=datetime.now()
                )
                suggestions.append(suggestion)

            # Suggest improvement for low success rate workflows
            if pattern.success_rate < 0.7:
                suggestion = ImprovementSuggestion(
                    suggestion_id=f"workflow_reliability_{pattern.pattern_id}",
                    suggestion_type="workflow",
                    description=f"Improve reliability of workflow: {pattern.pattern_data['workflow_id']} "
                               f"(success rate: {pattern.success_rate:.1%})",
                    confidence=0.9,
                    data={
                        "workflow_id": pattern.pattern_data["workflow_id"],
                        "current_success_rate": pattern.success_rate,
                        "frequency": pattern.frequency
                    },
                    created_at=datetime.now()
                )
                suggestions.append(suggestion)

        return suggestions

    def _generate_parameter_suggestions(self) -> List[ImprovementSuggestion]:
        """Generate suggestions for parameter improvements"""
        suggestions = []

        # Analyze parameter patterns
        param_patterns = [p for p in self.patterns if p.pattern_type == "parameter_choice"]

        for pattern in param_patterns:
            # Suggest default values for commonly used parameters
            if pattern.frequency >= 10 and pattern.success_rate >= 0.8:
                suggestion = ImprovementSuggestion(
                    suggestion_id=f"param_default_{pattern.pattern_id}",
                    suggestion_type="parameter",
                    description=f"Set default value for {pattern.pattern_data['parameter']} "
                               f"in {pattern.pattern_data['command']}: {pattern.pattern_data['common_value']}",
                    confidence=min(0.95, pattern.frequency / 20),
                    data={
                        "command": pattern.pattern_data["command"],
                        "parameter": pattern.pattern_data["parameter"],
                        "suggested_default": pattern.pattern_data["common_value"],
                        "usage_frequency": pattern.frequency
                    },
                    created_at=datetime.now()
                )
                suggestions.append(suggestion)

        return suggestions

    def _save_suggestions(self, suggestions: List[ImprovementSuggestion]):
        """Save suggestions to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for suggestion in suggestions:
                cursor.execute('''
                    INSERT OR REPLACE INTO suggestions
                    (suggestion_id, suggestion_type, description, confidence, data, created_at, implemented)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    suggestion.suggestion_id,
                    suggestion.suggestion_type,
                    suggestion.description,
                    suggestion.confidence,
                    json.dumps(suggestion.data),
                    suggestion.created_at.isoformat(),
                    suggestion.implemented
                ))

            conn.commit()

    def get_recommendations(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get personalized recommendations based on context"""
        recommendations = []

        # Get current patterns and suggestions
        if not self.patterns:
            asyncio.create_task(self.learn_patterns())

        if not self.suggestions:
            asyncio.create_task(self.generate_suggestions())

        # Context-aware recommendations
        if context.get("current_command"):
            # Suggest related commands based on patterns
            related_commands = self._get_related_commands(context["current_command"])
            recommendations.extend(related_commands)

        if context.get("workspace_type"):
            # Suggest workspace-specific improvements
            workspace_suggestions = self._get_workspace_suggestions(context["workspace_type"])
            recommendations.extend(workspace_suggestions)

        # Add general high-confidence suggestions
        general_suggestions = [
            {
                "type": "suggestion",
                "content": s.description,
                "confidence": s.confidence,
                "suggestion_id": s.suggestion_id
            }
            for s in self.suggestions[:5]  # Top 5 suggestions
            if s.confidence >= 0.9
        ]

        recommendations.extend(general_suggestions)

        return recommendations[:10]  # Limit to 10 recommendations

    def _get_related_commands(self, current_command: str) -> List[Dict[str, Any]]:
        """Get related commands based on sequence patterns"""
        related = []

        for pattern in self.patterns:
            if pattern.pattern_type == "command_sequence":
                sequence = pattern.pattern_data["sequence"]
                if current_command in sequence:
                    # Find commands that commonly follow the current command
                    current_index = sequence.index(current_command)
                    if current_index < len(sequence) - 1:
                        next_command = sequence[current_index + 1]
                        related.append({
                            "type": "next_command",
                            "content": f"Consider using: {next_command}",
                            "confidence": pattern.success_rate,
                            "frequency": pattern.frequency
                        })

        return related

    def _get_workspace_suggestions(self, workspace_type: str) -> List[Dict[str, Any]]:
        """Get workspace-specific suggestions"""
        suggestions = []

        # Analyze workspace-specific patterns
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT command_name, COUNT(*) as usage_count
                FROM learning_data
                WHERE context LIKE ? OR context LIKE ?
                GROUP BY command_name
                ORDER BY usage_count DESC
                LIMIT 5
            ''', (f'%"{workspace_type}"%', f'%workspace_type%'))

            popular_commands = cursor.fetchall()

        if popular_commands:
            suggestions.append({
                "type": "workspace_pattern",
                "content": f"Popular commands in {workspace_type}: {', '.join([cmd[0] for cmd in popular_commands[:3]])}",
                "confidence": 0.8,
                "data": {"popular_commands": popular_commands}
            })

        return suggestions

    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get usage statistics and insights"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total usage
            cursor.execute("SELECT COUNT(*) FROM learning_data")
            total_usage = cursor.fetchone()[0]

            # Success rate
            cursor.execute("SELECT COUNT(*) FROM learning_data WHERE success = 1")
            successful_usage = cursor.fetchone()[0]

            # Popular commands
            cursor.execute('''
                SELECT command_name, COUNT(*) as count
                FROM learning_data
                GROUP BY command_name
                ORDER BY count DESC
                LIMIT 10
            ''')
            popular_commands = cursor.fetchall()

            # Recent patterns
            cursor.execute('''
                SELECT pattern_type, COUNT(*) as count
                FROM patterns
                WHERE last_used > date('now', '-7 days')
                GROUP BY pattern_type
            ''')
            recent_patterns = cursor.fetchall()

            # Active suggestions
            cursor.execute("SELECT COUNT(*) FROM suggestions WHERE implemented = 0")
            active_suggestions = cursor.fetchone()[0]

        return {
            "total_usage": total_usage,
            "success_rate": successful_usage / total_usage if total_usage > 0 else 0,
            "popular_commands": popular_commands,
            "recent_patterns": recent_patterns,
            "active_suggestions": active_suggestions,
            "patterns_learned": len(self.patterns),
            "suggestions_generated": len(self.suggestions)
        }

    def implement_suggestion(self, suggestion_id: str) -> bool:
        """Mark a suggestion as implemented"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    UPDATE suggestions
                    SET implemented = 1
                    WHERE suggestion_id = ?
                ''', (suggestion_id,))

                conn.commit()

            return cursor.rowcount > 0

        except Exception as e:
            self.logger.error(f"Failed to implement suggestion: {e}")
            return False


# Global learning system instance
_learning_instance = None


def get_learning_system() -> LearningSystem:
    """Get or create the global learning system instance"""
    global _learning_instance
    if _learning_instance is None:
        _learning_instance = LearningSystem()
    return _learning_instance


# Utility functions
def record_command_usage(command_name: str, parameters: Dict[str, Any], execution_time: float,
                         success: bool, error_message: Optional[str] = None,
                         context: Optional[Dict[str, Any]] = None):
    """Record command usage for learning"""
    learning_system = get_learning_system()

    learning_data = LearningData(
        timestamp=datetime.now(),
        user_id=None,  # Would be populated from actual user context
        session_id="default",  # Would be populated from actual session
        command_name=command_name,
        parameters=parameters,
        execution_time=execution_time,
        success=success,
        error_message=error_message,
        context=context or {}
    )

    learning_system.record_usage(learning_data)


async def get_recommendations(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get learning-based recommendations"""
    learning_system = get_learning_system()
    return learning_system.get_recommendations(context)


async def get_usage_statistics() -> Dict[str, Any]:
    """Get usage statistics and insights"""
    learning_system = get_learning_system()
    return learning_system.get_usage_statistics()