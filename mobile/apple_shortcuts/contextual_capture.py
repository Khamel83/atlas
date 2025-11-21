"""
Contextual Capture Engine
Advanced capture with location, activity, and device context awareness
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import sys

sys.path.append(str(Path(__file__).parent.parent))
from helpers.config import load_config


@dataclass
class CaptureContext:
    """Enhanced capture context with device and environmental data"""

    location: Optional[Dict[str, float]] = None
    activity: Optional[str] = None  # walking, driving, stationary, etc.
    device_orientation: Optional[str] = None  # portrait, landscape
    battery_level: Optional[float] = None
    connectivity: Optional[str] = None  # wifi, cellular, offline
    time_zone: Optional[str] = None
    device_model: Optional[str] = None
    ios_version: Optional[str] = None
    app_usage_context: Optional[Dict[str, Any]] = None
    focus_mode: Optional[str] = None  # Do Not Disturb, Work, Personal, etc.
    calendar_context: Optional[Dict[str, Any]] = None
    previous_captures: Optional[List[str]] = None
    capture_frequency: Optional[Dict[str, int]] = None


@dataclass
class LocationContext:
    """Enhanced location context with semantic understanding"""

    latitude: float
    longitude: float
    accuracy: float
    altitude: Optional[float] = None
    speed: Optional[float] = None
    course: Optional[float] = None
    timestamp: Optional[str] = None
    semantic_location: Optional[str] = None  # "home", "work", "cafe", etc.
    location_confidence: Optional[float] = None
    nearby_places: Optional[List[str]] = None
    weather: Optional[Dict[str, Any]] = None


@dataclass
class ProcessingRecommendation:
    """AI-driven processing recommendations based on context"""

    priority: str  # urgent, high, normal, low
    processor: str  # immediate, batch, scheduled
    reasoning: str
    suggested_tags: List[str]
    suggested_category: str
    estimated_processing_time: int  # minutes
    context_score: float  # 0-1 confidence in context understanding
    automation_level: str  # full, assisted, manual


class ContextualCaptureEngine:
    """Advanced capture engine with context awareness and AI recommendations"""

    def __init__(self, config=None):
        self.config = config or load_config()
        self.db_path = str(
            Path(__file__).parent.parent / "data" / "podcasts" / "atlas_podcasts.db"
        )
        self._init_context_database()

        # Context analysis patterns
        self.location_patterns = {}
        self.activity_patterns = {}
        self.temporal_patterns = {}

        # Load existing patterns
        self._load_context_patterns()

    def _init_context_database(self):
        """Initialize enhanced context tracking database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Enhanced capture context table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS enhanced_capture_context (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        capture_id TEXT NOT NULL,
                        context_type TEXT NOT NULL,
                        context_data TEXT NOT NULL,
                        confidence_score REAL,
                        captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (capture_id) REFERENCES capture_queue(capture_id)
                    )
                """
                )

                # Location patterns table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS location_patterns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        semantic_location TEXT NOT NULL,
                        latitude REAL NOT NULL,
                        longitude REAL NOT NULL,
                        radius REAL NOT NULL,
                        confidence REAL NOT NULL,
                        usage_count INTEGER DEFAULT 1,
                        last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Activity patterns table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS activity_patterns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        activity_type TEXT NOT NULL,
                        content_types TEXT,  -- JSON array of common content types
                        time_patterns TEXT,  -- JSON array of common times
                        location_patterns TEXT,  -- JSON array of common locations
                        confidence REAL NOT NULL,
                        usage_count INTEGER DEFAULT 1,
                        last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Context learning table for ML improvements
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS context_learning (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        capture_id TEXT NOT NULL,
                        predicted_context TEXT,
                        actual_context TEXT,
                        accuracy_score REAL,
                        feedback_type TEXT,  -- automatic, manual
                        learned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                conn.commit()
        except Exception as e:
            print(f"Error initializing context database: {e}")

    def analyze_capture_context(self, capture_data: Dict[str, Any]) -> CaptureContext:
        """Analyze and enhance capture context with AI insights"""

        context = CaptureContext()

        # Extract basic context from capture data
        if "location" in capture_data:
            context.location = self._enhance_location_context(capture_data["location"])

        if "device_info" in capture_data:
            device_info = capture_data["device_info"]
            context.device_orientation = device_info.get("orientation")
            context.battery_level = device_info.get("battery_level")
            context.connectivity = device_info.get("connectivity")
            context.device_model = device_info.get("model")
            context.ios_version = device_info.get("ios_version")
            context.focus_mode = device_info.get("focus_mode")

        # Infer activity from sensor data and patterns
        if "activity_data" in capture_data:
            context.activity = self._infer_activity(capture_data["activity_data"])

        # Analyze temporal patterns
        context.time_zone = capture_data.get("time_zone")

        # Get calendar context if available
        if "calendar_context" in capture_data:
            context.calendar_context = capture_data["calendar_context"]

        # Analyze previous capture patterns
        context.previous_captures = self._get_recent_capture_patterns(
            capture_data.get("source_device")
        )

        # Calculate capture frequency patterns
        context.capture_frequency = self._calculate_capture_frequency(
            capture_data.get("source_device")
        )

        return context

    def _enhance_location_context(
        self, location_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance location data with semantic understanding"""

        enhanced_location = location_data.copy()

        # Check for known semantic locations
        semantic_location = self._identify_semantic_location(
            location_data.get("latitude"), location_data.get("longitude")
        )

        if semantic_location:
            enhanced_location["semantic_location"] = semantic_location
            enhanced_location["location_confidence"] = 0.9
        else:
            enhanced_location["location_confidence"] = 0.3

        # Add nearby places if available
        enhanced_location["nearby_places"] = self._get_nearby_places(
            location_data.get("latitude"), location_data.get("longitude")
        )

        return enhanced_location

    def _infer_activity(self, activity_data: Dict[str, Any]) -> str:
        """Infer current activity from sensor data and patterns"""

        # Simple activity inference based on motion data
        speed = activity_data.get("speed", 0)
        motion_confidence = activity_data.get("motion_confidence", 0)

        if speed < 1 and motion_confidence > 0.8:
            return "stationary"
        elif 1 <= speed < 10:
            return "walking"
        elif 10 <= speed < 50:
            return "driving"
        elif speed >= 50:
            return "traveling"
        else:
            return "unknown"

    def _identify_semantic_location(
        self, latitude: float, longitude: float
    ) -> Optional[str]:
        """Identify semantic location from coordinates"""

        if not latitude or not longitude:
            return None

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Find matching semantic locations within radius
                results = conn.execute(
                    """
                    SELECT semantic_location, confidence,
                           ((latitude - ?) * (latitude - ?) +
                            (longitude - ?) * (longitude - ?)) as distance_sq
                    FROM location_patterns
                    WHERE distance_sq <= (radius * radius)
                    ORDER BY confidence DESC, distance_sq ASC
                    LIMIT 1
                """,
                    (latitude, latitude, longitude, longitude),
                ).fetchone()

                if results and results["confidence"] > 0.7:
                    return results["semantic_location"]

        except Exception as e:
            print(f"Error identifying semantic location: {e}")

        return None

    def _get_nearby_places(self, latitude: float, longitude: float) -> List[str]:
        """Get nearby places of interest (placeholder for future enhancement)"""
        # This would integrate with Apple Maps/CoreLocation or similar service
        return []

    def _get_recent_capture_patterns(self, device_id: str) -> List[str]:
        """Get recent capture patterns for context analysis"""

        if not device_id:
            return []

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Get last 10 captures from this device
                results = conn.execute(
                    """
                    SELECT content_type, category, captured_at
                    FROM capture_queue
                    WHERE source_device = ?
                    ORDER BY captured_at DESC
                    LIMIT 10
                """,
                    (device_id,),
                ).fetchall()

                return [f"{row['content_type']}:{row['category']}" for row in results]

        except Exception as e:
            print(f"Error getting recent patterns: {e}")
            return []

    def _calculate_capture_frequency(self, device_id: str) -> Dict[str, int]:
        """Calculate capture frequency patterns"""

        if not device_id:
            return {}

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Get capture frequency for last 7 days
                week_ago = (datetime.now() - timedelta(days=7)).isoformat()

                results = conn.execute(
                    """
                    SELECT content_type, COUNT(*) as count
                    FROM capture_queue
                    WHERE source_device = ? AND captured_at > ?
                    GROUP BY content_type
                """,
                    (device_id, week_ago),
                ).fetchall()

                return {row["content_type"]: row["count"] for row in results}

        except Exception as e:
            print(f"Error calculating frequency: {e}")
            return {}

    def generate_processing_recommendations(
        self, content: str, content_type: str, context: CaptureContext
    ) -> ProcessingRecommendation:
        """Generate AI-driven processing recommendations based on context"""

        # Base recommendations
        priority = "normal"
        processor = "batch"
        reasoning = "Standard processing"
        suggested_tags = []
        suggested_category = "general"
        estimated_time = 15
        context_score = 0.5
        automation_level = "assisted"

        # Context-based adjustments
        if context.location and context.location.get("semantic_location"):
            semantic_loc = context.location["semantic_location"]

            if semantic_loc == "work":
                priority = "high"
                suggested_tags.append("work")
                suggested_category = "business"
                reasoning = "Captured at work location"
                context_score += 0.2

            elif semantic_loc == "home":
                suggested_tags.append("personal")
                reasoning = "Captured at home"
                context_score += 0.2

        # Activity-based adjustments
        if context.activity:
            if context.activity == "driving":
                priority = "urgent" if content_type == "voice" else "low"
                processor = "immediate" if content_type == "voice" else "scheduled"
                suggested_tags.append("mobile")
                reasoning = f"Captured while {context.activity}"
                context_score += 0.1

            elif context.activity == "walking":
                suggested_tags.append("mobile", "outdoor")
                context_score += 0.1

        # Focus mode adjustments
        if context.focus_mode:
            if context.focus_mode == "Work":
                suggested_category = "business"
                suggested_tags.append("work")
                context_score += 0.1
            elif context.focus_mode == "Personal":
                suggested_category = "personal"
                context_score += 0.1

        # Calendar context adjustments
        if context.calendar_context:
            if context.calendar_context.get("in_meeting"):
                priority = "urgent"
                processor = "immediate"
                suggested_tags.append("meeting")
                reasoning = "Captured during meeting"
                context_score += 0.2

        # Content type specific adjustments
        if content_type == "url":
            if any(domain in content for domain in ["github.com", "stackoverflow.com"]):
                suggested_category = "development"
                suggested_tags.append("coding")
                automation_level = "full"

        elif content_type == "voice":
            priority = "high"
            processor = "immediate"
            estimated_time = 5
            automation_level = "full"

        # Previous capture pattern analysis
        if context.previous_captures:
            recent_categories = [
                cap.split(":")[1] for cap in context.previous_captures if ":" in cap
            ]
            if recent_categories:
                most_common = max(set(recent_categories), key=recent_categories.count)
                if most_common != "general":
                    suggested_category = most_common
                    reasoning += f", following recent {most_common} pattern"
                    context_score += 0.1

        # Frequency analysis
        if context.capture_frequency:
            total_captures = sum(context.capture_frequency.values())
            if total_captures > 20:  # High frequency user
                automation_level = "full"
                context_score += 0.1

        # Ensure context score is within bounds
        context_score = min(1.0, context_score)

        return ProcessingRecommendation(
            priority=priority,
            processor=processor,
            reasoning=reasoning,
            suggested_tags=suggested_tags,
            suggested_category=suggested_category,
            estimated_processing_time=estimated_time,
            context_score=context_score,
            automation_level=automation_level,
        )

    def learn_from_context(
        self,
        capture_id: str,
        predicted_context: Dict[str, Any],
        actual_context: Dict[str, Any],
        feedback_type: str = "automatic",
    ):
        """Learn from context predictions for improved accuracy"""

        try:
            # Calculate accuracy score
            accuracy_score = self._calculate_context_accuracy(
                predicted_context, actual_context
            )

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO context_learning
                    (capture_id, predicted_context, actual_context, accuracy_score, feedback_type)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        capture_id,
                        json.dumps(predicted_context),
                        json.dumps(actual_context),
                        accuracy_score,
                        feedback_type,
                    ),
                )
                conn.commit()

            # Update patterns based on learning
            self._update_context_patterns(actual_context)

        except Exception as e:
            print(f"Error learning from context: {e}")

    def _calculate_context_accuracy(
        self, predicted: Dict[str, Any], actual: Dict[str, Any]
    ) -> float:
        """Calculate accuracy score between predicted and actual context"""

        if not predicted or not actual:
            return 0.0

        matches = 0
        total = 0

        # Compare common fields
        common_fields = ["category", "activity", "semantic_location", "priority"]

        for field in common_fields:
            if field in predicted and field in actual:
                total += 1
                if predicted[field] == actual[field]:
                    matches += 1

        return matches / total if total > 0 else 0.0

    def _update_context_patterns(self, context: Dict[str, Any]):
        """Update learned patterns based on actual context"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Update location patterns
                if "location" in context and "semantic_location" in context["location"]:
                    location = context["location"]
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO location_patterns
                        (semantic_location, latitude, longitude, radius, confidence)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            location["semantic_location"],
                            location.get("latitude", 0),
                            location.get("longitude", 0),
                            100,  # Default radius in meters
                            0.8,  # Initial confidence
                        ),
                    )

                    # Update usage count for existing patterns
                    conn.execute(
                        """
                        UPDATE location_patterns
                        SET usage_count = usage_count + 1, last_used = CURRENT_TIMESTAMP
                        WHERE semantic_location = ?
                    """,
                        (location["semantic_location"],),
                    )

                # Update activity patterns
                if "activity" in context:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO activity_patterns
                        (activity_type, confidence)
                        VALUES (?, ?)
                    """,
                        (context["activity"], 0.8),
                    )

                    conn.execute(
                        """
                        UPDATE activity_patterns
                        SET usage_count = usage_count + 1, last_used = CURRENT_TIMESTAMP
                        WHERE activity_type = ?
                    """,
                        (context["activity"],),
                    )

                conn.commit()

        except Exception as e:
            print(f"Error updating context patterns: {e}")

    def _load_context_patterns(self):
        """Load existing context patterns for quick access"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Load location patterns
                location_results = conn.execute(
                    """
                    SELECT * FROM location_patterns
                    WHERE confidence > 0.5
                    ORDER BY usage_count DESC
                """
                ).fetchall()

                self.location_patterns = {
                    row["semantic_location"]: dict(row) for row in location_results
                }

                # Load activity patterns
                activity_results = conn.execute(
                    """
                    SELECT * FROM activity_patterns
                    WHERE confidence > 0.5
                    ORDER BY usage_count DESC
                """
                ).fetchall()

                self.activity_patterns = {
                    row["activity_type"]: dict(row) for row in activity_results
                }

        except Exception as e:
            print(f"Error loading context patterns: {e}")

    def get_context_insights(self, days: int = 30) -> Dict[str, Any]:
        """Get insights about capture context patterns"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                since_date = (datetime.now() - timedelta(days=days)).isoformat()

                # Location insights
                location_stats = conn.execute(
                    """
                    SELECT semantic_location, COUNT(*) as count
                    FROM location_patterns lp
                    WHERE last_used > ?
                    GROUP BY semantic_location
                    ORDER BY count DESC
                """,
                    (since_date,),
                ).fetchall()

                # Activity insights
                activity_stats = conn.execute(
                    """
                    SELECT activity_type, COUNT(*) as count
                    FROM activity_patterns ap
                    WHERE last_used > ?
                    GROUP BY activity_type
                    ORDER BY count DESC
                """,
                    (since_date,),
                ).fetchall()

                # Context accuracy
                accuracy_stats = conn.execute(
                    """
                    SELECT AVG(accuracy_score) as avg_accuracy,
                           COUNT(*) as total_predictions
                    FROM context_learning
                    WHERE learned_at > ?
                """,
                    (since_date,),
                ).fetchone()

                return {
                    "location_patterns": [dict(row) for row in location_stats],
                    "activity_patterns": [dict(row) for row in activity_stats],
                    "prediction_accuracy": (
                        dict(accuracy_stats) if accuracy_stats else {}
                    ),
                    "insights_period_days": days,
                }

        except Exception as e:
            print(f"Error getting context insights: {e}")
            return {}
