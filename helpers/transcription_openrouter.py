import base64
import os

import requests


def transcribe_audio(audio_path):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "Missing OPENROUTER_API_KEY"

    with open(audio_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode()

    prompt = (
        "You are a transcription agent. Transcribe this audio accurately. "
        "Keep speaker labels if obvious, and use full punctuation."
    )

    payload = {
        "model": "google/gemini-1.5-flash-latest",
        "messages": [
            {"role": "user", "content": prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "audio",
                        "audio": {
                            "source": "base64",
                            "media_type": "audio/mp3",
                            "data": audio_b64,
                        },
                    }
                ],
            },
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://your-domain.com",  # optional
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"OpenRouter transcription failed: {e}")
        return "Transcription failed via OpenRouter"
