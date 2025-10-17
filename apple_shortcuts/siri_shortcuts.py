"""
Siri Shortcuts functionality for Atlas
"""

import json
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum


class ActionType(Enum):
    """Supported action types for Siri shortcuts"""

    LOG_ENTRY = "log_entry"
    START_TIMER = "start_timer"
    CREATE_NOTE = "create_note"
    CAPTURE_URL = "capture_url"
    VOICE_MEMO = "voice_memo"


@dataclass
class SiriShortcut:
    """Dataclass for Siri shortcut definitions"""

    name: str
    phrase: str
    action: ActionType
    parameters: Dict[str, Any]
    content_types: List[str]  # Supported content types (URL, text, voice, image, file)

    def __post_init__(self):
        """Validate parameters after initialization"""
        self.validate_parameters()

    def validate_parameters(self):
        """Validate parameters based on action type"""
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Name must be a non-empty string")

        if not isinstance(self.phrase, str) or not self.phrase.strip():
            raise ValueError("Phrase must be a non-empty string")

        if not isinstance(self.action, ActionType):
            raise ValueError("Action must be an ActionType enum")

        if not isinstance(self.parameters, dict):
            raise ValueError("Parameters must be a dictionary")

        if not isinstance(self.content_types, list):
            raise ValueError("Content types must be a list")

        # Validate content types with expanded list
        valid_content_types = ["URL", "text", "voice", "image", "file", "clipboard", "location", "contact"]
        for content_type in self.content_types:
            if content_type not in valid_content_types:
                raise ValueError(
                    f"Invalid content type: {content_type}. Valid types: {valid_content_types}"
                )

        # Enhanced parameter validation
        if len(self.name) > 100:
            raise ValueError("Name must be 100 characters or less")

        if len(self.phrase) > 200:
            raise ValueError("Phrase must be 200 characters or less")

        # Action-specific parameter validation
        if self.action == ActionType.LOG_ENTRY:
            if "type" not in self.parameters:
                raise ValueError("LOG_ENTRY action requires 'type' parameter")
        elif self.action == ActionType.START_TIMER:
            if "duration" in self.parameters and not isinstance(
                self.parameters["duration"], (int, float)
            ):
                raise ValueError("START_TIMER duration must be a number")
        elif self.action == ActionType.CREATE_NOTE:
            if "title" in self.parameters and not isinstance(
                self.parameters["title"], str
            ):
                raise ValueError("CREATE_NOTE title must be a string")
        elif self.action == ActionType.VOICE_MEMO:
            # Voice memo specific validation
            if "transcription" in self.parameters and not isinstance(
                self.parameters["transcription"], bool
            ):
                raise ValueError("VOICE_MEMO transcription parameter must be a boolean")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data["action"] = self.action.value
        return data


class ShortcutTemplate:
    """Template class for .shortcut file generation"""

    def __init__(self):
        pass

    def generate_shortcut_file(self, shortcut: SiriShortcut) -> Dict[str, Any]:
        """Generate a .shortcut file structure"""
        # This represents a more complete .shortcut file structure
        shortcut_data = {
            "WFWorkflowActions": [
                {
                    "WFWorkflowActionIdentifier": f"is.workflow.actions.{shortcut.action.value}",
                    "WFWorkflowActionParameters": {
                        "phrase": shortcut.phrase,
                        "parameters": shortcut.parameters,
                    },
                }
            ],
            "WFWorkflowIcon": {
                "WFWorkflowIconGlyphNumber": 59845,
                "WFWorkflowIconStartColor": 2071128575,
            },
            "WFWorkflowImportQuestions": [],
            "WFWorkflowInputContentItemClasses": [
                "WFAppStoreAppContentItem",
                "WFArticleContentItem",
                "WFContactContentItem",
                "WFDateContentItem",
                "WFEmailAddressContentItem",
                "WFGenericFileContentItem",
                "WFImageContentItem",
                "WFIMessageAttachmentContentItem",
                "WFMediaContentItem",
                "WFNumberContentItem",
                "WFPhoneNumberContentItem",
                "WFPhotoMediaContentItem",
                "WFReminderContentItem",
                "WFSafariWebPageContentItem",
                "WFStringContentItem",
                "WFURLContentItem",
            ],
            "WFWorkflowTypes": ["WatchKit", "ActionExtension"],
            "WFWorkflowClientVersion": "1040.24",
            "WFWorkflowClientRelease": "2.1",
            "WFWorkflowMinimumClientVersion": 900,
            "WFWorkflowMinimumClientRelease": "2.0",
        }
        return shortcut_data

    def generate_voice_capture_template(self) -> Dict[str, Any]:
        """Generate a template for voice-activated content capture"""
        template = {
            "WFWorkflowActions": [
                {
                    "WFWorkflowActionIdentifier": "is.workflow.actions.recordaudio",
                    "WFWorkflowActionParameters": {
                        "WFRecordingCompression": "Medium",
                        "WFRecordingStart": "Immediately",
                        "WFRecordingEnd": "After Time",
                        "WFRecordingTimeInterval": 300,  # 5 minutes
                    },
                },
                {
                    "WFWorkflowActionIdentifier": "is.workflow.actions.sendtoapp",
                    "WFWorkflowActionParameters": {
                        "WFAppName": "Atlas",
                        "WFInput": "Recorded Audio",
                    },
                },
            ],
            "WFWorkflowIcon": {
                "WFWorkflowIconGlyphNumber": 59845,
                "WFWorkflowIconStartColor": 2071128575,
            },
            "WFWorkflowImportQuestions": [],
            "WFWorkflowInputContentItemClasses": ["WFMediaContentItem"],
            "WFWorkflowTypes": ["WatchKit"],
            "WFWorkflowClientVersion": "1040.24",
            "WFWorkflowClientRelease": "2.1",
            "WFWorkflowMinimumClientVersion": 900,
            "WFWorkflowMinimumClientRelease": "2.0",
            "WFWorkflowName": "Hey Siri, save to Atlas",
            "WFWorkflowDescription": "Voice-activated content capture for Atlas",
        }
        return template

    def save_shortcut_file(self, shortcut: SiriShortcut, filepath: str) -> str:
        """Save a shortcut to a .shortcut file"""
        shortcut_data = self.generate_shortcut_file(shortcut)
        with open(filepath, "w") as f:
            json.dump(shortcut_data, f, indent=2)
        return filepath

    def save_voice_template(self, filepath: str) -> str:
        """Save the voice capture template to a .shortcut file"""
        template_data = self.generate_voice_capture_template()
        with open(filepath, "w") as f:
            json.dump(template_data, f, indent=2)
        return filepath


class SiriShortcutManager:
    """Manage Siri shortcuts for Atlas"""

    def __init__(self, shortcuts_dir: str = "shortcuts"):
        self.shortcuts_dir = shortcuts_dir
        os.makedirs(shortcuts_dir, exist_ok=True)
        self.template_generator = ShortcutTemplate()

    def create_shortcut(
        self,
        name: str,
        phrase: str,
        action: ActionType,
        parameters: Optional[Dict[str, Any]] = None,
        content_types: Optional[List[str]] = None,
    ) -> str:
        """Create a new Siri shortcut"""
        try:
            shortcut = SiriShortcut(
                name=name,
                phrase=phrase,
                action=action,
                parameters=parameters or {},
                content_types=content_types or ["text"],
            )
        except ValueError as e:
            raise ValueError(f"Invalid shortcut parameters: {e}")
        except Exception as e:
            raise Exception(f"Failed to create shortcut: {e}")

        # Save as JSON for internal use
        json_filepath = os.path.join(self.shortcuts_dir, f"{name}.json")
        try:
            with open(json_filepath, "w") as f:
                json.dump(shortcut.to_dict(), f, indent=2)
        except Exception as e:
            raise Exception(f"Failed to save shortcut JSON file: {e}")

        # Save as .shortcut file for iOS import
        shortcut_filepath = os.path.join(self.shortcuts_dir, f"{name}.shortcut")
        try:
            self.template_generator.save_shortcut_file(shortcut, shortcut_filepath)
        except Exception as e:
            raise Exception(f"Failed to save shortcut file: {e}")

        return json_filepath

    def create_voice_capture_shortcut(self) -> str:
        """Create the "Hey Siri, save to Atlas" voice capture shortcut"""
        filepath = os.path.join(self.shortcuts_dir, "hey_siri_save_to_atlas.shortcut")
        try:
            self.template_generator.save_voice_template(filepath)
            return filepath
        except Exception as e:
            raise Exception(f"Failed to create voice capture shortcut: {e}")

    def execute_shortcut(self, name: str) -> Dict[str, Any]:
        """Execute a Siri shortcut by name"""
        filepath = os.path.join(self.shortcuts_dir, f"{name}.json")
        if not os.path.exists(filepath):
            return {"error": f"Shortcut '{name}' not found"}

        try:
            with open(filepath, "r") as f:
                shortcut_data = json.load(f)
        except json.JSONDecodeError as e:
            return {"error": f"Malformed shortcut file for '{name}': {e}"}
        except Exception as e:
            return {"error": f"Failed to read shortcut file for '{name}': {e}"}

        # In a real implementation, this would actually execute the action
        # For now, we'll just return the shortcut data
        return {"status": "executed", "shortcut": shortcut_data}

    def list_shortcuts(self) -> Dict[str, Any]:
        """List all available shortcuts"""
        shortcuts = {}
        for filename in os.listdir(self.shortcuts_dir):
            if filename.endswith(".json"):
                name = filename[:-5]  # Remove .json extension
                filepath = os.path.join(self.shortcuts_dir, filename)
                try:
                    with open(filepath, "r") as f:
                        shortcuts[name] = json.load(f)
                except json.JSONDecodeError:
                    # Skip malformed files
                    continue
                except Exception:
                    # Skip files with other errors
                    continue
        return shortcuts

    def validate_shortcut_file(self, name: str) -> Dict[str, Any]:
        """Validate a shortcut file for errors"""
        filepath = os.path.join(self.shortcuts_dir, f"{name}.json")
        if not os.path.exists(filepath):
            return {"valid": False, "error": f"Shortcut '{name}' not found"}

        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            # Validate required fields
            required_fields = ["name", "phrase", "action"]
            for field in required_fields:
                if field not in data:
                    return {"valid": False, "error": f"Missing required field: {field}"}

            # Validate action
            try:
                ActionType(data["action"])
            except ValueError:
                return {"valid": False, "error": f"Invalid action: {data['action']}"}

            return {"valid": True, "message": "Shortcut file is valid"}

        except json.JSONDecodeError as e:
            return {"valid": False, "error": f"Malformed JSON: {e}"}
        except Exception as e:
            return {"valid": False, "error": f"Validation error: {e}"}

    def process_voice_memo(
        self, audio_data: bytes, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a voice memo with transcription"""
        try:
            import tempfile
            import os
            from datetime import datetime

            # Save audio data to temporary file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            with tempfile.NamedTemporaryFile(
                suffix=f"_{timestamp}.wav", delete=False
            ) as temp_file:
                temp_file.write(audio_data)
                audio_path = temp_file.name

            try:
                # Attempt to use Atlas transcription system
                transcript = self._transcribe_audio(audio_path)

                # Analyze the transcript
                analysis = self._analyze_transcript(transcript)

                base_result = {
                    "status": "processed",
                    "transcript": transcript,
                    "confidence": analysis.get("confidence", 0.85),
                    "language": analysis.get("language", "en"),
                    "duration": self._estimate_duration(audio_data),
                    "speaker_count": analysis.get("speaker_count", 1),
                    "emotional_tone": analysis.get("emotional_tone", "neutral"),
                    "key_topics": analysis.get("key_topics", []),
                    "action_items": analysis.get("action_items", []),
                    "summary": analysis.get(
                        "summary", "Voice memo captured via Siri shortcut"
                    ),
                    "processing_time": analysis.get("processing_time", 0.1),
                    "audio_quality": analysis.get("audio_quality", "good"),
                    "audio_file_path": audio_path,
                }

                # Add automatic categorization
                categories = self._categorize_speech_content(transcript)
                base_result["categories"] = categories

                return base_result

            finally:
                # Clean up temporary file
                try:
                    os.unlink(audio_path)
                except Exception:
                    pass  # Best effort cleanup

        except Exception as e:
            # Fallback to basic processing
            return {
                "status": "error",
                "error": str(e),
                "transcript": "[Transcription failed]",
                "confidence": 0.0,
                "language": "unknown",
                "duration": self._estimate_duration(audio_data),
                "categories": ["voice_memo", "personal"],
                "summary": "Voice memo captured but processing failed",
            }

    def _transcribe_audio(self, audio_path: str) -> str:
        """Transcribe audio using available transcription services"""
        try:
            # Try using OpenAI Whisper API if available
            if os.getenv("OPENAI_API_KEY"):
                return self._transcribe_with_openai(audio_path)
        except Exception as e:
            print(f"OpenAI transcription failed: {e}")

        try:
            # Try local Whisper if available
            return self._transcribe_with_local_whisper(audio_path)
        except Exception as e:
            print(f"Local Whisper transcription failed: {e}")

        # Fallback message
        return "[Audio transcription not available - configure OpenAI API key or install Whisper]"

    def _transcribe_with_openai(self, audio_path: str) -> str:
        """Transcribe using OpenAI Whisper API"""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            with open(audio_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", file=audio_file, response_format="text"
                )

            return transcript
        except ImportError:
            raise Exception("OpenAI library not available")

    def _transcribe_with_local_whisper(self, audio_path: str) -> str:
        """Transcribe using local Whisper installation"""
        try:
            import whisper

            model = whisper.load_model("base")
            result = model.transcribe(audio_path)
            return result["text"]
        except ImportError:
            raise Exception("Local Whisper not available")

    def _analyze_transcript(self, transcript: str) -> Dict[str, Any]:
        """Analyze transcript for additional insights"""
        analysis = {
            "confidence": 0.85,
            "language": "en",
            "speaker_count": 1,
            "emotional_tone": "neutral",
            "key_topics": [],
            "action_items": [],
            "summary": "",
            "processing_time": 0.1,
            "audio_quality": "good",
        }

        if not transcript or transcript.strip() == "":
            return analysis

        text_lower = transcript.lower()

        # Extract action items
        action_indicators = [
            "need to",
            "have to",
            "should",
            "must",
            "remind",
            "don't forget",
        ]
        for indicator in action_indicators:
            if indicator in text_lower:
                # Simple extraction - in practice, this could be more sophisticated
                sentences = transcript.split(".")
                for sentence in sentences:
                    if indicator in sentence.lower():
                        analysis["action_items"].append(sentence.strip())

        # Determine emotional tone
        positive_words = ["happy", "great", "excellent", "love", "wonderful", "amazing"]
        negative_words = ["sad", "angry", "frustrated", "terrible", "hate", "awful"]

        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count > negative_count:
            analysis["emotional_tone"] = "positive"
        elif negative_count > positive_count:
            analysis["emotional_tone"] = "negative"

        # Extract key topics (simple keyword-based)
        topic_keywords = {
            "work": ["work", "job", "meeting", "project", "deadline"],
            "health": ["doctor", "exercise", "health", "medicine"],
            "finance": ["money", "budget", "investment", "expense"],
            "personal": ["family", "friend", "home", "personal"],
        }

        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                analysis["key_topics"].append(topic)

        # Generate summary
        if len(transcript) > 100:
            analysis["summary"] = transcript[:100] + "..."
        else:
            analysis["summary"] = transcript

        return analysis

    def _estimate_duration(self, audio_data: bytes) -> float:
        """Estimate audio duration from byte length"""
        # Very rough estimate assuming 16-bit, 44.1kHz mono
        # This is just a placeholder - real implementation would parse audio headers
        return len(audio_data) / (44100 * 2)

    def _categorize_speech_content(self, transcript: str) -> List[str]:
        """Automatically categorize speech content based on keywords"""
        categories = []

        # Convert to lowercase for case-insensitive matching
        text_lower = transcript.lower()

        # Category keywords
        category_keywords = {
            "meeting": [
                "meeting",
                "discuss",
                "agenda",
                "action items",
                "follow up",
                "attendees",
                "conference call",
            ],
            "idea": [
                "idea",
                "thought",
                "concept",
                "brainstorm",
                "innovation",
                "creative",
                "brainstorming",
            ],
            "task": [
                "task",
                "todo",
                "remind",
                "schedule",
                "plan",
                "organize",
                "deadline",
                "due date",
                "need to",
                "have to",
            ],
            "learning": [
                "learn",
                "study",
                "book",
                "article",
                "research",
                "education",
                "course",
                "lecture",
                "exam",
            ],
            "health": [
                "health",
                "exercise",
                "workout",
                "medicine",
                "doctor",
                "fitness",
                "wellness",
                "diet",
            ],
            "finance": [
                "money",
                "budget",
                "finance",
                "investment",
                "expense",
                "income",
                "invest",
                "stocks",
                "bank",
            ],
            "personal": [
                "personal",
                "family",
                "friend",
                "relationship",
                "life",
                "home",
                "house",
            ],
            "work": [
                "work",
                "job",
                "career",
                "project",
                "client",
                "colleague",
                "office",
                "business",
            ],
            "shopping": [
                "buy",
                "purchase",
                "shop",
                "store",
                "grocery",
                "wishlist",
                "shopping",
                "mall",
            ],
            "travel": [
                "travel",
                "trip",
                "vacation",
                "flight",
                "hotel",
                "destination",
                "airport",
                "journey",
            ],
        }

        # Match keywords to categories
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    categories.append(category)
                    break  # Only add category once

        # If no categories found, default to personal
        if not categories:
            categories = ["personal"]

        return categories
