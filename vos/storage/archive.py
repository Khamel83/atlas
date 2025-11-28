from pathlib import Path


def archive_html(html: str, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / "content.html"
    with path.open("w", encoding="utf-8") as f:
        f.write(html)
    return path


def archive_text(text: str, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / "content.txt"
    with path.open("w", encoding="utf-8") as f:
        f.write(text)
    return path
