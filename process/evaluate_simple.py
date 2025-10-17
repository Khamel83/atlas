# process/evaluate_simple.py - Simplified OpenRouter-only version

import json
import requests
from typing import Optional
import yaml


def simple_openrouter_call(messages, config, temperature=0.3):
    """Ultra-simple OpenRouter call - auto-select cheapest model"""
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config.get('OPENROUTER_API_KEY')}",
                "Content-Type": "application/json",
            },
            json={
                "model": "auto",  # Auto-select cheapest
                "messages": messages,
                "temperature": temperature,
            },
        )
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"OpenRouter API error: {e}")
        return None


def classify_content(content: str, config: dict) -> Optional[str]:
    """Classifies content into categories using OpenRouter."""
    if not config.get("OPENROUTER_API_KEY"):
        return "general"

    messages = [
        {
            "role": "system",
            "content": "Classify this content into one category: technology, finance, politics, science, culture, or general. Return only the category name.",
        },
        {"role": "user", "content": content[:1000]},  # Limit for speed
    ]
    return simple_openrouter_call(messages, config) or "general"


def summarize_content(text: str, config: dict) -> Optional[str]:
    """Summarizes content using OpenRouter auto-selection."""
    if not config.get("OPENROUTER_API_KEY"):
        return None

    messages = [
        {
            "role": "system",
            "content": "You are an expert summarizer. Provide a concise summary of the following text.",
        },
        {"role": "user", "content": text},
    ]
    return simple_openrouter_call(messages, config)


def extract_entities(text: str, config: dict) -> Optional[dict]:
    """Extracts key entities from text using OpenRouter."""
    if not config.get("OPENROUTER_API_KEY"):
        return {}

    messages = [
        {
            "role": "system",
            "content": "Extract key people, organizations, locations, and topics from this text. Return JSON with keys 'people', 'organizations', 'locations', 'topics'.",
        },
        {"role": "user", "content": text[:2000]},  # Limit for speed
    ]

    result = simple_openrouter_call(messages, config)
    if result:
        try:
            return json.loads(result)
        except:
            return {}
    return {}


# Dummy functions for compatibility
def diarize_speakers(text: str, config: dict) -> list:
    """Placeholder - not implemented"""
    return []


def get_content_type(url: str) -> str:
    """Simple content type detection"""
    if "youtube.com" in url or "youtu.be" in url:
        return "video"
    elif any(ext in url.lower() for ext in [".pdf", ".doc", ".docx"]):
        return "document"
    else:
        return "article"
