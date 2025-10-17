import subprocess
from pathlib import Path



def transcribe_audio(audio_path: str) -> str:
    """
    Transcribes audio using Whisper.
    Returns transcript as plain text.
    """
    output_path = Path(audio_path).with_suffix(".txt")

    try:
        subprocess.run(
            [
                "whisper",
                audio_path,
                "--model",
                "base.en",
                "--output_format",
                "txt",
                "--output_dir",
                str(Path(audio_path).parent),
            ],
            check=True,
        )

        with open(output_path, "r") as f:
            return f.read()

    except subprocess.CalledProcessError as e:
        print(f"Error during transcription: {e}")
        return ""

    except FileNotFoundError:
        print("Whisper not installed or not in PATH.")
        return ""
