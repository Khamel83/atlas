# Atlas Technical Stack

## Application Foundation
- **Primary Language**: Python 3.9+
- **Web Framework**: FastAPI 0.116.1
- **ASGI Server**: uvicorn 0.35.0
- **Template Engine**: Jinja2 3.1.6
- **Job Scheduler**: APScheduler 3.11.0

## Content Processing
- **Web Scraping**: requests 2.32.4, playwright 1.53.0, playwright-stealth 2.0.0
- **HTML Processing**: BeautifulSoup4 4.13.4, lxml 6.0.0, readability-lxml 0.8.4.1
- **Content Extraction**: html2text 2025.4.15, markdownify 1.1.0
- **YouTube Processing**: pytube 15.0.0, youtube-transcript-api 1.1.1
- **Podcast Processing**: feedparser 6.0.11

## AI and LLM Integration
- **LLM Routing**: litellm 1.74.6
- **OpenAI API**: openai 1.97.0
- **Model Management**: tiktoken 0.9.0, tokenizers 0.21.2
- **AI Processing**: huggingface-hub 0.33.4

## Data Management
- **Configuration**: python-dotenv 1.1.1, PyYAML 6.0.2
- **Validation**: pydantic 2.11.7, jsonschema 4.25.0
- **Database ORM**: SQLAlchemy 2.0.41
- **File Processing**: defusedxml 0.7.1

## Development Tools
- **Testing**: pytest 8.4.1, pytest-mock 3.14.1, responses 0.25.7
- **Code Quality**: black, isort, mypy
- **Type Checking**: typing_extensions 4.14.1, annotated-types 0.7.0

## Networking and HTTP
- **HTTP Client**: httpx 0.28.1, aiohttp 3.12.14
- **URL Processing**: urllib3 2.5.0, idna 3.10
- **Network Utilities**: aiohappyeyeballs 2.6.1

## User Interface
- **Rich Terminal**: rich 14.0.0, click 8.1.8
- **Progress Tracking**: tqdm 4.67.1
- **Markdown Processing**: markdown-it-py 3.0.0, Pygments 2.19.2

## Deployment & Infrastructure
- **Preferred Target**: Raspberry Pi (self-hosting, low-power operation)
- **Development**: Mac Mini M4 16GB (intensive processing tasks)
- **Storage Strategy**: Local filesystem with extensive spinning disk storage
- **Process Management**: Systemd services for production deployment

## Security & Privacy
- **Data Encryption**: Built-in Python cryptography
- **Local Storage**: All data stored locally, no cloud dependencies
- **API Security**: Rate limiting, authentication tokens
- **Privacy First**: No external data transmission except for configured API calls

## Architecture Patterns
- **Strategy Pattern**: Multi-layer content extraction fallbacks
- **Template Method**: Base ingestor classes for extensibility
- **Observer Pattern**: Event-driven processing pipeline
- **Factory Pattern**: Content type processors and AI model selection
- **Dependency Injection**: Configuration and service management