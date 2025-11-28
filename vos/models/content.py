from dataclasses import dataclass
from typing import Optional

@dataclass
class ContentRecord:
    id: str
    title: str
    url: str
    source: str
    content_type: str
    text_path: str
    html_path: str
    created_at: str
    metadata: dict
