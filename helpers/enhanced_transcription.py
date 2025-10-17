#!/usr/bin/env python3
"""
Enhanced Multi-Provider Transcription System

Supports multiple transcription providers and models:
- Local Whisper (tiny, small, medium, large, turbo)
- OpenAI Whisper API
- OpenRouter API (Gemini, GPT-4 Audio)
- AssemblyAI
- Deepgram

Provides speed vs accuracy testing and comparison capabilities.
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum
import requests
import base64
from dataclasses import dataclass

from .utils import log_info, log_error


class TranscriptionProvider(Enum):
    """Available transcription providers"""
    WHISPER_LOCAL = "whisper_local"
    WHISPER_API = "whisper_api"
    OPENROUTER = "openrouter"
    ASSEMBLYAI = "assemblyai"
    DEEPGRAM = "deepgram"


class WhisperModel(Enum):
    """Whisper model sizes ordered by speed (fastest to slowest)"""
    TINY = "tiny"          # ~32x faster, lowest accuracy
    SMALL = "small"        # ~16x faster, medium accuracy
    MEDIUM = "medium"      # ~4x faster, good accuracy
    LARGE = "large"        # ~2x faster, high accuracy
    TURBO = "turbo"        # New fastest large model


@dataclass
class TranscriptionResult:
    """Result of a transcription operation"""
    text: str
    provider: TranscriptionProvider
    model: str
    duration_seconds: float
    confidence: Optional[float] = None
    word_count: int = 0
    error: Optional[str] = None

    def __post_init__(self):
        if self.text:
            self.word_count = len(self.text.split())


class EnhancedTranscriptionEngine:
    """Enhanced transcription engine supporting multiple providers and models"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.results_cache = {}

        # API keys
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.assemblyai_key = os.getenv("ASSEMBLYAI_API_KEY")
        self.deepgram_key = os.getenv("DEEPGRAM_API_KEY")

    def transcribe_with_all_models(self, audio_path: str, log_path: str) -> Dict[str, TranscriptionResult]:
        """Transcribe audio with all available models for comparison"""
        results = {}

        log_info(log_path, f"Starting comprehensive transcription of {audio_path}")

        # Test all local Whisper models
        for model in WhisperModel:
            try:
                result = self.transcribe_whisper_local(audio_path, model.value, log_path)
                results[f"whisper_local_{model.value}"] = result
            except Exception as e:
                log_error(log_path, f"Local Whisper {model.value} failed: {e}")
                results[f"whisper_local_{model.value}"] = TranscriptionResult(
                    text="", provider=TranscriptionProvider.WHISPER_LOCAL,
                    model=model.value, duration_seconds=0, error=str(e)
                )

        # Test OpenAI Whisper API
        if self.openai_key:
            try:
                result = self.transcribe_openai_api(audio_path, log_path)
                results["openai_whisper_api"] = result
            except Exception as e:
                log_error(log_path, f"OpenAI API failed: {e}")

        # Test OpenRouter
        if self.openrouter_key:
            try:
                result = self.transcribe_openrouter(audio_path, log_path)
                results["openrouter"] = result
            except Exception as e:
                log_error(log_path, f"OpenRouter failed: {e}")

        # Test AssemblyAI
        if self.assemblyai_key:
            try:
                result = self.transcribe_assemblyai(audio_path, log_path)
                results["assemblyai"] = result
            except Exception as e:
                log_error(log_path, f"AssemblyAI failed: {e}")

        # Test Deepgram
        if self.deepgram_key:
            try:
                result = self.transcribe_deepgram(audio_path, log_path)
                results["deepgram"] = result
            except Exception as e:
                log_error(log_path, f"Deepgram failed: {e}")

        log_info(log_path, f"Completed transcription with {len(results)} providers")
        return results

    def transcribe_whisper_local(self, audio_path: str, model: str, log_path: str) -> TranscriptionResult:
        """Transcribe using local Whisper installation"""
        start_time = time.time()

        output_dir = Path(audio_path).parent
        transcript_path = output_dir / f"{Path(audio_path).stem}_{model}.txt"

        # Check cache
        if transcript_path.exists():
            log_info(log_path, f"Using cached transcript for {model}")
            transcript = transcript_path.read_text()
            return TranscriptionResult(
                text=transcript,
                provider=TranscriptionProvider.WHISPER_LOCAL,
                model=model,
                duration_seconds=0  # Cached, no timing
            )

        try:
            # Build Whisper command
            command = [
                str(Path(sys.executable).parent / "whisper"),
                str(audio_path),
                "--model", model,
                "--output_format", "txt",
                "--output_dir", str(output_dir),
                "--language", "en",
                "--fp16", "False",  # Better compatibility
                "--no_speech_threshold", "0.6"
            ]

            log_info(log_path, f"Running Whisper {model} model...")

            # Run transcription
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()

            duration = time.time() - start_time

            if process.returncode != 0:
                raise Exception(f"Whisper failed: {stderr}")

            # Find and read the generated transcript
            generated_file = output_dir / f"{Path(audio_path).stem}.txt"
            if generated_file.exists():
                transcript = generated_file.read_text().strip()

                # Save with model-specific name
                transcript_path.write_text(transcript)

                # Clean up original file
                generated_file.unlink()

                log_info(log_path, f"Whisper {model} completed in {duration:.2f}s")

                return TranscriptionResult(
                    text=transcript,
                    provider=TranscriptionProvider.WHISPER_LOCAL,
                    model=model,
                    duration_seconds=duration
                )
            else:
                raise Exception("Transcript file not generated")

        except FileNotFoundError:
            raise Exception("Whisper not installed or not in PATH")
        except Exception as e:
            duration = time.time() - start_time
            raise Exception(f"Whisper {model} transcription failed: {e}")

    def transcribe_openai_api(self, audio_path: str, log_path: str) -> TranscriptionResult:
        """Transcribe using OpenAI Whisper API"""
        start_time = time.time()

        try:
            with open(audio_path, "rb") as audio_file:
                response = requests.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={
                        "Authorization": f"Bearer {self.openai_key}"
                    },
                    files={
                        "file": (Path(audio_path).name, audio_file, "audio/mpeg")
                    },
                    data={
                        "model": "whisper-1",
                        "language": "en",
                        "response_format": "verbose_json"
                    },
                    timeout=300
                )

            response.raise_for_status()
            result = response.json()

            duration = time.time() - start_time

            return TranscriptionResult(
                text=result.get("text", ""),
                provider=TranscriptionProvider.WHISPER_API,
                model="whisper-1",
                duration_seconds=duration,
                confidence=result.get("confidence")
            )

        except Exception as e:
            duration = time.time() - start_time
            raise Exception(f"OpenAI API transcription failed: {e}")

    def transcribe_openrouter(self, audio_path: str, log_path: str) -> TranscriptionResult:
        """Transcribe using OpenRouter (Gemini Flash)"""
        start_time = time.time()

        try:
            with open(audio_path, "rb") as f:
                audio_b64 = base64.b64encode(f.read()).decode()

            payload = {
                "model": "google/gemini-1.5-flash",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Transcribe this audio accurately with proper punctuation. Return only the transcript."
                            },
                            {
                                "type": "audio",
                                "audio": {
                                    "source": "base64",
                                    "media_type": "audio/mpeg",
                                    "data": audio_b64
                                }
                            }
                        ]
                    }
                ]
            }

            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_key}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=300
            )

            response.raise_for_status()
            result = response.json()

            duration = time.time() - start_time

            transcript = result["choices"][0]["message"]["content"]

            return TranscriptionResult(
                text=transcript,
                provider=TranscriptionProvider.OPENROUTER,
                model="gemini-1.5-flash",
                duration_seconds=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            raise Exception(f"OpenRouter transcription failed: {e}")

    def transcribe_assemblyai(self, audio_path: str, log_path: str) -> TranscriptionResult:
        """Transcribe using AssemblyAI"""
        start_time = time.time()

        try:
            # Upload file
            with open(audio_path, "rb") as f:
                upload_response = requests.post(
                    "https://api.assemblyai.com/v2/upload",
                    headers={"authorization": self.assemblyai_key},
                    files={"file": f}
                )
            upload_response.raise_for_status()
            upload_url = upload_response.json()["upload_url"]

            # Request transcription
            transcript_response = requests.post(
                "https://api.assemblyai.com/v2/transcript",
                headers={"authorization": self.assemblyai_key},
                json={
                    "audio_url": upload_url,
                    "language_code": "en"
                }
            )
            transcript_response.raise_for_status()
            transcript_id = transcript_response.json()["id"]

            # Poll for completion
            while True:
                result_response = requests.get(
                    f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                    headers={"authorization": self.assemblyai_key}
                )
                result_response.raise_for_status()
                result = result_response.json()

                if result["status"] == "completed":
                    break
                elif result["status"] == "error":
                    raise Exception(f"AssemblyAI error: {result.get('error')}")

                time.sleep(2)

            duration = time.time() - start_time

            return TranscriptionResult(
                text=result.get("text", ""),
                provider=TranscriptionProvider.ASSEMBLYAI,
                model="best",
                duration_seconds=duration,
                confidence=result.get("confidence")
            )

        except Exception as e:
            duration = time.time() - start_time
            raise Exception(f"AssemblyAI transcription failed: {e}")

    def transcribe_deepgram(self, audio_path: str, log_path: str) -> TranscriptionResult:
        """Transcribe using Deepgram"""
        start_time = time.time()

        try:
            with open(audio_path, "rb") as audio_file:
                response = requests.post(
                    "https://api.deepgram.com/v1/listen",
                    headers={
                        "Authorization": f"Token {self.deepgram_key}",
                        "Content-Type": "audio/mpeg"
                    },
                    params={
                        "model": "nova-2",
                        "language": "en",
                        "punctuate": "true",
                        "utterances": "true"
                    },
                    data=audio_file,
                    timeout=300
                )

            response.raise_for_status()
            result = response.json()

            duration = time.time() - start_time

            # Extract transcript
            transcript = ""
            if "results" in result and "channels" in result["results"]:
                alternatives = result["results"]["channels"][0]["alternatives"]
                if alternatives:
                    transcript = alternatives[0]["transcript"]
                    confidence = alternatives[0].get("confidence", 0)

            return TranscriptionResult(
                text=transcript,
                provider=TranscriptionProvider.DEEPGRAM,
                model="nova-2",
                duration_seconds=duration,
                confidence=confidence
            )

        except Exception as e:
            duration = time.time() - start_time
            raise Exception(f"Deepgram transcription failed: {e}")

    def get_fastest_transcription(self, audio_path: str, log_path: str) -> TranscriptionResult:
        """Get transcription using the fastest available method"""
        # Try tiny model first (fastest)
        try:
            return self.transcribe_whisper_local(audio_path, WhisperModel.TINY.value, log_path)
        except Exception:
            pass

        # Fallback to OpenRouter if available
        if self.openrouter_key:
            try:
                return self.transcribe_openrouter(audio_path, log_path)
            except Exception:
                pass

        # Fallback to small model
        try:
            return self.transcribe_whisper_local(audio_path, WhisperModel.SMALL.value, log_path)
        except Exception as e:
            raise Exception(f"All fast transcription methods failed: {e}")

    try:
            return self.transcribe_whisper_local(audio_path, WhisperModel.TINY.value, log_path)
        except Exception:
            pass

        # Fallback to OpenRouter if available
        if self.openrouter_key:
            try:
                return self.transcribe_openrouter(audio_path, log_path)
            except Exception:
                pass

        # Fallback to small model
        try:
            return self.transcribe_whisper_local(audio_path, WhisperModel.SMALL.value, log_path)
        except Exception as e:
            raise Exception(f"All fast transcription methods failed: {e}")

    def get_highest_quality_transcription(self, audio_path: str, log_path: str) -> TranscriptionResult:
        """Get transcription using the highest quality method available"""
        # Try large model first
        try:
            return self.transcribe_whisper_local(audio_path, WhisperModel.LARGE.value, log_path)
        except Exception:
            pass

        # Try AssemblyAI (generally high quality)
        if self.assemblyai_key:
            try:
                return self.transcribe_assemblyai(audio_path, log_path)
            except Exception:
                pass

        # Try OpenAI API
        if self.openai_key:
            try:
                return self.transcribe_openai_api(audio_path, log_path)
            except Exception:
                pass

    def compare_transcription_quality(self, audio_path: str, ground_truth: str, log_path: str) -> Dict[str, Any]:
        """Compare all transcription methods against ground truth"""
        all_results = self.transcribe_with_all_models(audio_path, log_path)

        comparison = {
            "ground_truth": ground_truth,
            "results": {},
            "ranking": []
        }

        for provider_model, result in all_results.items():
            if result.error:
                continue

            # Calculate similarity metrics
            similarity = self._calculate_similarity(ground_truth, result.text)

            comparison["results"][provider_model] = {
                "transcript": result.text,
                "duration": result.duration_seconds,
                "word_count": result.word_count,
                "similarity_score": similarity["word_similarity"],
                "word_error_rate": similarity["word_error_rate"],
                "character_accuracy": similarity["character_similarity"],
                "speed_score": result.word_count / result.duration_seconds if result.duration_seconds > 0 else 0
            }

        # Rank by quality (similarity score)
        ranking = sorted(
            comparison["results"].items(),
            key=lambda x: x[1]["similarity_score"],
            reverse=True
        )
        comparison["ranking"] = [{"provider": name, **data} for name, data in ranking]

        return comparison

    def _calculate_similarity(self, reference: str, hypothesis: str) -> Dict[str, float]:
        """Calculate similarity metrics between reference and hypothesis"""
        import difflib

        # Word-level comparison
        ref_words = reference.lower().split()
        hyp_words = hypothesis.lower().split()

        # Calculate similarity
        sequence_matcher = difflib.SequenceMatcher(None, ref_words, hyp_words)
        word_similarity = sequence_matcher.ratio()

        # Character-level similarity
        char_similarity = difflib.SequenceMatcher(None, reference.lower(), hypothesis.lower()).ratio()

        # Word Error Rate (WER)
        wer = self._calculate_wer(ref_words, hyp_words)

        return {
            "word_similarity": word_similarity,
            "character_similarity": char_similarity,
            "word_error_rate": wer
        }

    def _calculate_wer(self, reference: List[str], hypothesis: List[str]) -> float:
        """Calculate Word Error Rate using edit distance"""
        # Initialize matrix
        d = [[0] * (len(hypothesis) + 1) for _ in range(len(reference) + 1)]

        # Fill first row and column
        for i in range(len(reference) + 1):
            d[i][0] = i
        for j in range(len(hypothesis) + 1):
            d[0][j] = j

        # Fill matrix
        for i in range(1, len(reference) + 1):
            for j in range(1, len(hypothesis) + 1):
                if reference[i-1] == hypothesis[j-1]:
                    d[i][j] = d[i-1][j-1]
                else:
                    d[i][j] = min(d[i-1][j], d[i][j-1], d[i-1][j-1]) + 1

        # Return WER
        return d[len(reference)][len(hypothesis)] / len(reference) if reference else 0.0


# Convenience functions for backward compatibility
def transcribe_audio_fast(audio_path: str, log_path: str, config: Dict[str, Any]) -> str:
    """Get fast transcription (tiny model or API)"""
    engine = EnhancedTranscriptionEngine(config)
    result = engine.get_fastest_transcription(audio_path, log_path)
    return result.text

def transcribe_audio_quality(audio_path: str, log_path: str, config: Dict[str, Any]) -> str:
    """Get high-quality transcription (large model or premium API)"""
    engine = EnhancedTranscriptionEngine(config)
    result = engine.get_highest_quality_transcription(audio_path, log_path)
    return result.text

def transcribe_audio_all(audio_path: str, log_path: str, config: Dict[str, Any]) -> Dict[str, TranscriptionResult]:
    """Get transcription from all available providers"""
    engine = EnhancedTranscriptionEngine(config)
    return engine.transcribe_with_all_models(audio_path, log_path)