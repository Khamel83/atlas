"""
Advanced Voice Processing System
Enhanced voice memo processing with transcription, analysis, and smart categorization
"""

import json
import sqlite3
import aiofiles
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import hashlib
import sys

sys.path.append(str(Path(__file__).parent.parent))
from helpers.config import load_config


@dataclass
class VoiceProcessingResult:
    """Results from voice processing"""

    transcript: str
    confidence: float
    language: str
    duration: float
    speaker_count: int
    emotional_tone: Optional[str] = None
    key_topics: Optional[List[str]] = None
    action_items: Optional[List[str]] = None
    summary: Optional[str] = None
    timestamps: Optional[List[Dict[str, Any]]] = None
    processing_time: Optional[float] = None
    audio_quality: Optional[str] = None
    noise_level: Optional[float] = None


@dataclass
class VoiceMetadata:
    """Enhanced voice recording metadata"""

    file_path: str
    file_size: int
    duration: float
    sample_rate: int
    channels: int
    bit_depth: int
    format: str
    checksum: str
    recorded_at: datetime
    device_info: Optional[Dict[str, Any]] = None
    location: Optional[Dict[str, Any]] = None
    app_context: Optional[str] = None
    recording_quality: Optional[str] = None


@dataclass
class SpeakerSegment:
    """Speaker diarization segment"""

    speaker_id: str
    start_time: float
    end_time: float
    text: str
    confidence: float


class VoiceProcessor:
    """Advanced voice processing with transcription, analysis, and intelligence"""

    def __init__(self, config=None):
        self.config = config or load_config()
        self.db_path = str(
            Path(__file__).parent.parent / "data" / "podcasts" / "atlas_podcasts.db"
        )
        self.voice_storage = Path(__file__).parent.parent / "data" / "voice_recordings"
        self.voice_storage.mkdir(parents=True, exist_ok=True)

        # Initialize transcription backends
        self.transcription_backends = self._init_transcription_backends()

        # Initialize database
        self._init_voice_database()

        # Audio processing settings
        self.supported_formats = {".m4a", ".wav", ".mp3", ".aac", ".opus", ".flac"}
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.max_duration = 3600  # 1 hour

    def _init_transcription_backends(self) -> Dict[str, Any]:
        """Initialize available transcription backends"""
        backends = {}

        # OpenAI Whisper (local)
        try:
            import whisper

            backends["whisper_local"] = {
                "available": True,
                "models": ["tiny", "base", "small", "medium", "large"],
                "languages": "auto",
                "quality": "high",
                "speed": "medium",
            }
        except ImportError:
            backends["whisper_local"] = {"available": False}

        # OpenRouter API
        if self.config.get("openrouter_api_key"):
            backends["openrouter"] = {
                "available": True,
                "models": ["whisper-1"],
                "languages": "auto",
                "quality": "high",
                "speed": "fast",
            }
        else:
            backends["openrouter"] = {"available": False}

        # Speech Recognition (fallback)
        try:
            import speech_recognition as sr

            backends["speech_recognition"] = {
                "available": True,
                "models": ["google", "sphinx"],
                "languages": "limited",
                "quality": "medium",
                "speed": "fast",
            }
        except ImportError:
            backends["speech_recognition"] = {"available": False}

        return backends

    def _init_voice_database(self):
        """Initialize voice processing database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Voice recordings table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS voice_recordings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        capture_id TEXT UNIQUE NOT NULL,
                        file_path TEXT NOT NULL,
                        file_checksum TEXT NOT NULL,
                        duration REAL NOT NULL,
                        file_size INTEGER NOT NULL,
                        audio_format TEXT NOT NULL,
                        sample_rate INTEGER,
                        channels INTEGER,
                        bit_depth INTEGER,
                        recorded_at TIMESTAMP NOT NULL,
                        processed_at TIMESTAMP,
                        processing_status TEXT DEFAULT 'pending',
                        transcription_backend TEXT,
                        device_info TEXT,
                        location_data TEXT,
                        app_context TEXT,
                        recording_quality TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Voice transcriptions table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS voice_transcriptions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        recording_id INTEGER NOT NULL,
                        transcript TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        language TEXT NOT NULL,
                        transcription_backend TEXT NOT NULL,
                        processing_time REAL,
                        speaker_count INTEGER DEFAULT 1,
                        emotional_tone TEXT,
                        audio_quality TEXT,
                        noise_level REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (recording_id) REFERENCES voice_recordings(id)
                    )
                """
                )

                # Speaker diarization table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS speaker_segments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        transcription_id INTEGER NOT NULL,
                        speaker_id TEXT NOT NULL,
                        start_time REAL NOT NULL,
                        end_time REAL NOT NULL,
                        text TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (transcription_id) REFERENCES voice_transcriptions(id)
                    )
                """
                )

                # Voice analysis table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS voice_analysis (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        transcription_id INTEGER NOT NULL,
                        analysis_type TEXT NOT NULL,  -- topics, sentiment, actions, summary
                        analysis_result TEXT NOT NULL,  -- JSON data
                        confidence REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (transcription_id) REFERENCES voice_transcriptions(id)
                    )
                """
                )

                # Voice processing queue
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS voice_processing_queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        recording_id INTEGER NOT NULL,
                        priority INTEGER DEFAULT 5,
                        processing_type TEXT NOT NULL,  -- transcribe, analyze, enhance
                        attempts INTEGER DEFAULT 0,
                        last_attempt TIMESTAMP,
                        error_message TEXT,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (recording_id) REFERENCES voice_recordings(id)
                    )
                """
                )

                # Create indexes for performance
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_voice_recordings_capture_id ON voice_recordings(capture_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_voice_recordings_status ON voice_recordings(processing_status)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_voice_transcriptions_recording ON voice_transcriptions(recording_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_speaker_segments_transcription ON speaker_segments(transcription_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_voice_analysis_transcription ON voice_analysis(transcription_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_voice_queue_status ON voice_processing_queue(status)"
                )

                conn.commit()
        except Exception as e:
            print(f"Error initializing voice database: {e}")

    async def process_voice_recording(
        self, audio_data: bytes, capture_id: str, metadata: Dict[str, Any] = None
    ) -> VoiceProcessingResult:
        """Process voice recording with transcription and analysis"""

        try:
            # Save audio file
            voice_metadata = await self._save_voice_recording(
                audio_data, capture_id, metadata
            )

            # Add to processing queue
            recording_id = await self._queue_voice_processing(voice_metadata)

            # Process immediately for high priority or small files
            if self._should_process_immediately(voice_metadata, metadata):
                result = await self._process_voice_immediate(
                    recording_id, voice_metadata
                )
            else:
                # Queue for batch processing
                result = await self._queue_for_batch_processing(
                    recording_id, voice_metadata
                )

            return result

        except Exception as e:
            print(f"Error processing voice recording: {e}")
            return VoiceProcessingResult(
                transcript="",
                confidence=0.0,
                language="unknown",
                duration=0.0,
                speaker_count=0,
            )

    async def _save_voice_recording(
        self, audio_data: bytes, capture_id: str, metadata: Dict[str, Any] = None
    ) -> VoiceMetadata:
        """Save voice recording and extract metadata"""

        # Generate file path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = metadata.get("format", ".m4a")
        filename = f"voice_{timestamp}_{capture_id[:8]}{file_extension}"
        file_path = self.voice_storage / filename

        # Save audio data
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(audio_data)

        # Calculate checksum
        checksum = hashlib.md5(audio_data).hexdigest()

        # Extract audio metadata
        audio_metadata = await self._extract_audio_metadata(file_path, audio_data)

        # Create voice metadata
        voice_metadata = VoiceMetadata(
            file_path=str(file_path),
            file_size=len(audio_data),
            duration=audio_metadata.get("duration", 0.0),
            sample_rate=audio_metadata.get("sample_rate", 44100),
            channels=audio_metadata.get("channels", 1),
            bit_depth=audio_metadata.get("bit_depth", 16),
            format=file_extension,
            checksum=checksum,
            recorded_at=metadata.get("recorded_at", datetime.now()),
            device_info=metadata.get("device_info"),
            location=metadata.get("location"),
            app_context=metadata.get("app_context"),
            recording_quality=audio_metadata.get("quality", "unknown"),
        )

        # Save to database
        await self._save_voice_metadata(capture_id, voice_metadata)

        return voice_metadata

    async def _extract_audio_metadata(
        self, file_path: Path, audio_data: bytes
    ) -> Dict[str, Any]:
        """Extract audio metadata using available libraries"""

        metadata = {}

        try:
            # Try using pydub for metadata extraction
            try:
                from pydub import AudioSegment

                audio_segment = AudioSegment.from_file(file_path)

                metadata.update(
                    {
                        "duration": len(audio_segment) / 1000.0,  # Convert to seconds
                        "sample_rate": audio_segment.frame_rate,
                        "channels": audio_segment.channels,
                        "bit_depth": audio_segment.sample_width * 8,
                        "quality": (
                            "high" if audio_segment.frame_rate >= 44100 else "medium"
                        ),
                    }
                )

            except ImportError:
                # Fallback to basic file size analysis
                metadata.update(
                    {
                        "duration": len(audio_data) / (44100 * 2),  # Rough estimate
                        "sample_rate": 44100,
                        "channels": 1,
                        "bit_depth": 16,
                        "quality": "unknown",
                    }
                )

        except Exception as e:
            print(f"Error extracting audio metadata: {e}")
            metadata = {
                "duration": 0.0,
                "sample_rate": 44100,
                "channels": 1,
                "bit_depth": 16,
                "quality": "unknown",
            }

        return metadata

    async def _save_voice_metadata(self, capture_id: str, metadata: VoiceMetadata):
        """Save voice metadata to database"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO voice_recordings
                    (capture_id, file_path, file_checksum, duration, file_size, audio_format,
                     sample_rate, channels, bit_depth, recorded_at, device_info, location_data,
                     app_context, recording_quality)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        capture_id,
                        metadata.file_path,
                        metadata.checksum,
                        metadata.duration,
                        metadata.file_size,
                        metadata.format,
                        metadata.sample_rate,
                        metadata.channels,
                        metadata.bit_depth,
                        metadata.recorded_at.isoformat(),
                        (
                            json.dumps(metadata.device_info)
                            if metadata.device_info
                            else None
                        ),
                        json.dumps(metadata.location) if metadata.location else None,
                        metadata.app_context,
                        metadata.recording_quality,
                    ),
                )
                conn.commit()

        except Exception as e:
            print(f"Error saving voice metadata: {e}")

    def _should_process_immediately(
        self, metadata: VoiceMetadata, capture_metadata: Dict[str, Any] = None
    ) -> bool:
        """Determine if voice should be processed immediately"""

        # Process immediately if:
        # - Duration is less than 2 minutes
        # - High priority context (meeting, urgent)
        # - Voice memo app context
        # - Driving activity detected

        if metadata.duration < 120:  # 2 minutes
            return True

        if capture_metadata:
            priority = capture_metadata.get("priority", "normal")
            if priority in ["urgent", "high"]:
                return True

            activity = capture_metadata.get("activity")
            if activity == "driving":
                return True

            app_context = capture_metadata.get("app_context")
            if app_context in ["voice_memos", "dictation", "meeting"]:
                return True

        return False

    async def _queue_voice_processing(self, metadata: VoiceMetadata) -> int:
        """Queue voice recording for processing and return recording ID"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get recording ID
                result = conn.execute(
                    """
                    SELECT id FROM voice_recordings WHERE file_path = ?
                """,
                    (metadata.file_path,),
                ).fetchone()

                if not result:
                    raise Exception("Recording not found in database")

                recording_id = result[0]

                # Add to processing queue
                conn.execute(
                    """
                    INSERT INTO voice_processing_queue
                    (recording_id, processing_type, priority)
                    VALUES (?, ?, ?)
                """,
                    (recording_id, "transcribe", 5),
                )

                conn.commit()
                return recording_id

        except Exception as e:
            print(f"Error queuing voice processing: {e}")
            return 0

    async def _process_voice_immediate(
        self, recording_id: int, metadata: VoiceMetadata
    ) -> VoiceProcessingResult:
        """Process voice recording immediately"""

        try:
            # Select best transcription backend
            backend = self._select_transcription_backend(metadata)

            # Transcribe audio
            transcript_result = await self._transcribe_audio(
                metadata.file_path, backend
            )

            # Save transcription
            transcription_id = await self._save_transcription(
                recording_id, transcript_result, backend
            )

            # Perform advanced analysis
            analysis_result = await self._analyze_transcription(
                transcription_id, transcript_result
            )

            # Update processing status
            await self._update_processing_status(recording_id, "completed")

            # Combine results
            result = VoiceProcessingResult(
                transcript=transcript_result.get("text", ""),
                confidence=transcript_result.get("confidence", 0.0),
                language=transcript_result.get("language", "unknown"),
                duration=metadata.duration,
                speaker_count=transcript_result.get("speaker_count", 1),
                emotional_tone=analysis_result.get("emotional_tone"),
                key_topics=analysis_result.get("key_topics", []),
                action_items=analysis_result.get("action_items", []),
                summary=analysis_result.get("summary"),
                timestamps=transcript_result.get("timestamps", []),
                processing_time=transcript_result.get("processing_time"),
                audio_quality=transcript_result.get("audio_quality"),
                noise_level=transcript_result.get("noise_level"),
            )

            return result

        except Exception as e:
            print(f"Error in immediate voice processing: {e}")
            await self._update_processing_status(recording_id, "failed", str(e))
            return VoiceProcessingResult(
                transcript="",
                confidence=0.0,
                language="unknown",
                duration=metadata.duration,
                speaker_count=0,
            )

    def _select_transcription_backend(self, metadata: VoiceMetadata) -> str:
        """Select best transcription backend based on audio characteristics"""

        # Factors to consider:
        # - Audio quality
        # - Duration
        # - Available backends
        # - Performance requirements

        available_backends = [
            name
            for name, info in self.transcription_backends.items()
            if info.get("available", False)
        ]

        if not available_backends:
            return "none"

        # For high quality, longer recordings, prefer local Whisper
        if (
            metadata.recording_quality == "high"
            and metadata.duration > 60
            and "whisper_local" in available_backends
        ):
            return "whisper_local"

        # For quick processing, prefer OpenRouter
        if "openrouter" in available_backends:
            return "openrouter"

        # Fallback to local Whisper
        if "whisper_local" in available_backends:
            return "whisper_local"

        # Last resort
        return available_backends[0]

    async def _transcribe_audio(self, file_path: str, backend: str) -> Dict[str, Any]:
        """Transcribe audio using selected backend"""

        start_time = datetime.now()

        try:
            if backend == "whisper_local":
                result = await self._transcribe_with_whisper_local(file_path)
            elif backend == "openrouter":
                result = await self._transcribe_with_openrouter(file_path)
            elif backend == "speech_recognition":
                result = await self._transcribe_with_speech_recognition(file_path)
            else:
                raise Exception(f"Unsupported backend: {backend}")

            # Add processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            result["processing_time"] = processing_time
            result["backend"] = backend

            return result

        except Exception as e:
            print(f"Error transcribing with {backend}: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "language": "unknown",
                "error": str(e),
                "backend": backend,
                "processing_time": (datetime.now() - start_time).total_seconds(),
            }

    async def _transcribe_with_whisper_local(self, file_path: str) -> Dict[str, Any]:
        """Transcribe using local Whisper model"""

        try:
            import whisper

            # Select model based on file characteristics
            model_name = self._select_whisper_model(file_path)
            model = whisper.load_model(model_name)

            # Transcribe
            result = model.transcribe(file_path, verbose=True)

            return {
                "text": result["text"].strip(),
                "confidence": 0.95,  # Whisper doesn't provide word-level confidence
                "language": result["language"],
                "segments": result.get("segments", []),
                "timestamps": [
                    {"start": seg["start"], "end": seg["end"], "text": seg["text"]}
                    for seg in result.get("segments", [])
                ],
                "speaker_count": 1,  # Default, would need diarization for multiple speakers
                "audio_quality": "good",
                "model": model_name,
            }

        except Exception as e:
            print(f"Whisper local transcription error: {e}")
            raise

    async def _transcribe_with_openrouter(self, file_path: str) -> Dict[str, Any]:
        """Transcribe using OpenRouter API"""

        try:
            import aiohttp

            api_key = self.config.get("openrouter_api_key")
            if not api_key:
                raise Exception("OpenRouter API key not configured")

            # Read audio file
            async with aiofiles.open(file_path, "rb") as f:
                audio_data = await f.read()

            # Prepare request
            headers = {
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://atlas-local.com",
                "X-Title": "Atlas Voice Processing",
            }

            # Create form data
            form_data = aiohttp.FormData()
            form_data.add_field("file", audio_data, filename=Path(file_path).name)
            form_data.add_field("model", "whisper-1")
            form_data.add_field("response_format", "verbose_json")

            # Make API request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/audio/transcriptions",
                    headers=headers,
                    data=form_data,
                ) as response:

                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"OpenRouter API error: {error_text}")

                    result = await response.json()

                    return {
                        "text": result.get("text", "").strip(),
                        "confidence": 0.9,  # OpenRouter/Whisper generally high quality
                        "language": result.get("language", "unknown"),
                        "segments": result.get("segments", []),
                        "timestamps": [
                            {
                                "start": seg.get("start", 0),
                                "end": seg.get("end", 0),
                                "text": seg.get("text", ""),
                            }
                            for seg in result.get("segments", [])
                        ],
                        "speaker_count": 1,
                        "audio_quality": "good",
                    }

        except Exception as e:
            print(f"OpenRouter transcription error: {e}")
            raise

    async def _transcribe_with_speech_recognition(
        self, file_path: str
    ) -> Dict[str, Any]:
        """Transcribe using speech_recognition library (fallback)"""

        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()

            # Convert to WAV if needed
            audio_file = await self._convert_to_wav(file_path)

            with sr.AudioFile(audio_file) as source:
                audio = recognizer.record(source)

            # Transcribe with Google Speech Recognition
            text = recognizer.recognize_google(audio)

            return {
                "text": text.strip(),
                "confidence": 0.7,  # Lower confidence for basic SR
                "language": "en",  # Default to English
                "segments": [],
                "timestamps": [],
                "speaker_count": 1,
                "audio_quality": "medium",
            }

        except Exception as e:
            print(f"Speech recognition error: {e}")
            raise

    def _select_whisper_model(self, file_path: str) -> str:
        """Select appropriate Whisper model based on file characteristics"""

        # For this implementation, use base model as default
        # Could be enhanced to select based on:
        # - File duration
        # - Available system resources
        # - Quality requirements
        return "base"

    async def _convert_to_wav(self, file_path: str) -> str:
        """Convert audio file to WAV format for speech_recognition"""

        try:
            from pydub import AudioSegment

            # Load audio
            audio = AudioSegment.from_file(file_path)

            # Convert to WAV
            wav_path = file_path.replace(Path(file_path).suffix, ".wav")
            audio.export(wav_path, format="wav")

            return wav_path

        except ImportError:
            # If pydub not available, assume file is already compatible
            return file_path

    async def _save_transcription(
        self, recording_id: int, transcript_result: Dict[str, Any], backend: str
    ) -> int:
        """Save transcription result to database"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO voice_transcriptions
                    (recording_id, transcript, confidence, language, transcription_backend,
                     processing_time, speaker_count, audio_quality, noise_level)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        recording_id,
                        transcript_result.get("text", ""),
                        transcript_result.get("confidence", 0.0),
                        transcript_result.get("language", "unknown"),
                        backend,
                        transcript_result.get("processing_time"),
                        transcript_result.get("speaker_count", 1),
                        transcript_result.get("audio_quality"),
                        transcript_result.get("noise_level"),
                    ),
                )

                transcription_id = cursor.lastrowid

                # Save speaker segments if available
                segments = transcript_result.get("segments", [])
                for i, segment in enumerate(segments):
                    conn.execute(
                        """
                        INSERT INTO speaker_segments
                        (transcription_id, speaker_id, start_time, end_time, text, confidence)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            transcription_id,
                            f"speaker_{i % transcript_result.get('speaker_count', 1)}",
                            segment.get("start", 0),
                            segment.get("end", 0),
                            segment.get("text", ""),
                            segment.get("confidence", 0.9),
                        ),
                    )

                conn.commit()
                return transcription_id

        except Exception as e:
            print(f"Error saving transcription: {e}")
            return 0

    async def _analyze_transcription(
        self, transcription_id: int, transcript_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform advanced analysis on transcription"""

        text = transcript_result.get("text", "")
        if not text:
            return {}

        analysis_results = {}

        try:
            # Key topics extraction
            topics = await self._extract_key_topics(text)
            analysis_results["key_topics"] = topics

            # Action items detection
            action_items = await self._detect_action_items(text)
            analysis_results["action_items"] = action_items

            # Emotional tone analysis
            emotional_tone = await self._analyze_emotional_tone(text)
            analysis_results["emotional_tone"] = emotional_tone

            # Summary generation
            summary = await self._generate_summary(text)
            analysis_results["summary"] = summary

            # Save analysis results
            await self._save_analysis_results(transcription_id, analysis_results)

        except Exception as e:
            print(f"Error analyzing transcription: {e}")

        return analysis_results

    async def _extract_key_topics(self, text: str) -> List[str]:
        """Extract key topics from transcribed text"""

        # Simple keyword extraction (could be enhanced with NLP)
        import re

        # Common topic keywords
        topic_patterns = [
            r"\b(?:project|work|meeting|task|deadline|budget|client|customer)\b",
            r"\b(?:idea|concept|strategy|plan|goal|objective|target)\b",
            r"\b(?:issue|problem|challenge|solution|fix|resolve)\b",
            r"\b(?:schedule|calendar|appointment|event|reminder)\b",
        ]

        topics = []
        for pattern in topic_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            topics.extend(set(matches))

        return list(set(topics))[:10]  # Limit to top 10

    async def _detect_action_items(self, text: str) -> List[str]:
        """Detect action items from transcribed text"""

        import re

        # Action item patterns
        action_patterns = [
            r"(?:need to|have to|must|should|will|going to)\s+([^.!?]+)",
            r"(?:remind me to|remember to|don\'t forget to)\s+([^.!?]+)",
            r"(?:action item|action|task|todo):\s*([^.!?]+)",
            r"(?:follow up|follow-up)\s+(?:on|with)\s+([^.!?]+)",
        ]

        action_items = []
        for pattern in action_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            action_items.extend([match.strip() for match in matches])

        return action_items[:5]  # Limit to 5 action items

    async def _analyze_emotional_tone(self, text: str) -> str:
        """Analyze emotional tone of the text"""

        # Simple sentiment analysis based on keywords
        positive_words = [
            "good",
            "great",
            "excellent",
            "positive",
            "happy",
            "excited",
            "pleased",
        ]
        negative_words = [
            "bad",
            "terrible",
            "negative",
            "sad",
            "angry",
            "frustrated",
            "worried",
        ]
        neutral_words = ["okay", "fine", "normal", "regular", "standard"]

        text_lower = text.lower()

        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        neutral_count = sum(1 for word in neutral_words if word in text_lower)

        if positive_count > negative_count and positive_count > neutral_count:
            return "positive"
        elif negative_count > positive_count and negative_count > neutral_count:
            return "negative"
        else:
            return "neutral"

    async def _generate_summary(self, text: str) -> str:
        """Generate summary of the transcribed text"""

        # Simple extractive summary (first and last sentences)
        sentences = text.split(". ")

        if len(sentences) <= 2:
            return text

        # Take first sentence and last sentence for basic summary
        summary = f"{sentences[0]}. {sentences[-1]}"

        return summary[:200]  # Limit to 200 characters

    async def _save_analysis_results(
        self, transcription_id: int, results: Dict[str, Any]
    ):
        """Save analysis results to database"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                for analysis_type, result in results.items():
                    conn.execute(
                        """
                        INSERT INTO voice_analysis
                        (transcription_id, analysis_type, analysis_result, confidence)
                        VALUES (?, ?, ?, ?)
                    """,
                        (
                            transcription_id,
                            analysis_type,
                            json.dumps(result),
                            0.8,  # Default confidence
                        ),
                    )

                conn.commit()

        except Exception as e:
            print(f"Error saving analysis results: {e}")

    async def _update_processing_status(
        self, recording_id: int, status: str, error_message: str = None
    ):
        """Update processing status in database"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                if error_message:
                    conn.execute(
                        """
                        UPDATE voice_recordings
                        SET processing_status = ?, processed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """,
                        (status, recording_id),
                    )

                    conn.execute(
                        """
                        UPDATE voice_processing_queue
                        SET status = ?, error_message = ?
                        WHERE recording_id = ?
                    """,
                        (status, error_message, recording_id),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE voice_recordings
                        SET processing_status = ?, processed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """,
                        (status, recording_id),
                    )

                    conn.execute(
                        """
                        UPDATE voice_processing_queue
                        SET status = ?
                        WHERE recording_id = ?
                    """,
                        (status, recording_id),
                    )

                conn.commit()

        except Exception as e:
            print(f"Error updating processing status: {e}")

    async def _queue_for_batch_processing(
        self, recording_id: int, metadata: VoiceMetadata
    ) -> VoiceProcessingResult:
        """Queue for batch processing and return placeholder result"""

        return VoiceProcessingResult(
            transcript="[Processing queued - will be available soon]",
            confidence=0.0,
            language="unknown",
            duration=metadata.duration,
            speaker_count=1,
        )

    async def process_queued_recordings(
        self, batch_size: int = 5
    ) -> List[Dict[str, Any]]:
        """Process queued voice recordings in batch"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Get pending recordings
                pending = conn.execute(
                    """
                    SELECT vpq.*, vr.*
                    FROM voice_processing_queue vpq
                    JOIN voice_recordings vr ON vpq.recording_id = vr.id
                    WHERE vpq.status = 'pending'
                    ORDER BY vpq.priority DESC, vpq.created_at ASC
                    LIMIT ?
                """,
                    (batch_size,),
                ).fetchall()

                results = []

                for record in pending:
                    try:
                        # Create metadata object
                        metadata = VoiceMetadata(
                            file_path=record["file_path"],
                            file_size=record["file_size"],
                            duration=record["duration"],
                            sample_rate=record["sample_rate"],
                            channels=record["channels"],
                            bit_depth=record["bit_depth"],
                            format=record["audio_format"],
                            checksum=record["file_checksum"],
                            recorded_at=datetime.fromisoformat(record["recorded_at"]),
                            recording_quality=record["recording_quality"],
                        )

                        # Process recording
                        result = await self._process_voice_immediate(
                            record["recording_id"], metadata
                        )

                        results.append(
                            {
                                "recording_id": record["recording_id"],
                                "capture_id": record["capture_id"],
                                "success": True,
                                "result": asdict(result),
                            }
                        )

                    except Exception as e:
                        print(
                            f"Error processing recording {record['recording_id']}: {e}"
                        )
                        await self._update_processing_status(
                            record["recording_id"], "failed", str(e)
                        )

                        results.append(
                            {
                                "recording_id": record["recording_id"],
                                "capture_id": record["capture_id"],
                                "success": False,
                                "error": str(e),
                            }
                        )

                return results

        except Exception as e:
            print(f"Error processing queued recordings: {e}")
            return []

    def get_voice_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get voice processing statistics"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                since_date = (datetime.now() - timedelta(days=days)).isoformat()

                # Basic statistics
                basic_stats = conn.execute(
                    """
                    SELECT
                        COUNT(*) as total_recordings,
                        SUM(duration) as total_duration,
                        AVG(duration) as avg_duration,
                        SUM(file_size) as total_size,
                        COUNT(CASE WHEN processing_status = 'completed' THEN 1 END) as completed,
                        COUNT(CASE WHEN processing_status = 'pending' THEN 1 END) as pending,
                        COUNT(CASE WHEN processing_status = 'failed' THEN 1 END) as failed
                    FROM voice_recordings
                    WHERE recorded_at > ?
                """,
                    (since_date,),
                ).fetchone()

                # Transcription quality
                quality_stats = conn.execute(
                    """
                    SELECT
                        AVG(confidence) as avg_confidence,
                        COUNT(DISTINCT language) as languages_detected,
                        transcription_backend,
                        COUNT(*) as backend_usage
                    FROM voice_transcriptions vt
                    JOIN voice_recordings vr ON vt.recording_id = vr.id
                    WHERE vr.recorded_at > ?
                    GROUP BY transcription_backend
                """,
                    (since_date,),
                ).fetchall()

                # Top topics
                top_topics = conn.execute(
                    """
                    SELECT analysis_result, COUNT(*) as frequency
                    FROM voice_analysis va
                    JOIN voice_transcriptions vt ON va.transcription_id = vt.id
                    JOIN voice_recordings vr ON vt.recording_id = vr.id
                    WHERE va.analysis_type = 'key_topics' AND vr.recorded_at > ?
                    GROUP BY analysis_result
                    ORDER BY frequency DESC
                    LIMIT 10
                """,
                    (since_date,),
                ).fetchall()

                return {
                    "basic_statistics": dict(basic_stats) if basic_stats else {},
                    "quality_statistics": [dict(row) for row in quality_stats],
                    "top_topics": [dict(row) for row in top_topics],
                    "period_days": days,
                }

        except Exception as e:
            print(f"Error getting voice statistics: {e}")
            return {}
