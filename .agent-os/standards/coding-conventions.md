# Coding Conventions

## Overview

This document outlines the coding conventions for the TrojanHorse project. Adhering to these conventions ensures code consistency, readability, and maintainability across the codebase, facilitating collaboration and reducing the likelihood of errors.

## General Principles

- **Readability:** Code should be easy to read and understand by humans.
- **Consistency:** Follow existing patterns and styles within the codebase.
- **Simplicity:** Prefer simple, straightforward solutions over complex ones.
- **Clarity:** Code should clearly express its intent.
- **DRY (Don't Repeat Yourself):** Avoid redundant code.

## Python Specific Conventions

### 1. PEP 8 Compliance

- All Python code must adhere to [PEP 8](https://www.python.org/dev/peps/pep-0008/), the official style guide for Python code.
- **Tool:** Use `flake8` or `ruff` for automated PEP 8 checking.

### 2. Naming Conventions

- **Modules:** `lowercase_with_underscores` (e.g., `audio_capture.py`).
- **Packages:** `lowercase_with_underscores` (e.g., `my_package`).
- **Classes:** `CamelCase` (e.g., `AudioCaptureManager`).
- **Functions and Methods:** `lowercase_with_underscores` (e.g., `process_audio_chunk`).
- **Variables:** `lowercase_with_underscores` (e.g., `file_path`, `chunk_duration`).
- **Constants:** `UPPERCASE_WITH_UNDERSCORES` (e.g., `DEFAULT_SAMPLE_RATE`).
- **Private Members:** Prefix with a single underscore (e.g., `_private_method`).
- **Protected Members:** Prefix with a double underscore (e.g., `__protected_attribute`).

### 3. Imports

- Imports should be grouped in the following order:
    1.  Standard library imports.
    2.  Third-party imports.
    3.  Local application/library specific imports.
- Each group should be separated by a blank line.
- Imports should be sorted alphabetically within each group.
- **Tool:** Use `isort` for automated import sorting.

```python
import os
import sys

import requests
from pynacl.secret import SecretBox

from .utils import helper_function
from my_package.sub_module import MyClass
```

### 4. Docstrings

- All modules, classes, and public functions/methods should have docstrings.
- Use [Google Style Docstrings](https://google.github.io/styleguide/pyguide.html#pyguide-documenting-code) for consistency.

```python
def calculate_sum(a, b):
    """Calculates the sum of two numbers.

    Args:
        a: The first number.
        b: The second number.

    Returns:
        The sum of a and b.
    """
    return a + b
```

### 5. Comments

- Use comments sparingly, focusing on *why* something is done, not *what* is done.
- Keep comments up-to-date with the code.
- Use inline comments for small clarifications.

### 6. Whitespace

- Use 4 spaces for indentation.
- No hard tabs.
- Limit lines to 79 characters (as per PEP 8).
- Use blank lines to separate logical blocks of code.

### 7. Type Hinting

- Use type hints for function arguments, return values, and variables where appropriate.
- **Tool:** Use `mypy` for static type checking.

```python
def greet(name: str) -> str:
    return f"Hello, {name}"

my_list: list[int] = [1, 2, 3]
```

### 8. Error Handling

- Follow the guidelines outlined in `error-handling-guidelines.md`.

### 9. Configuration

- All configurable parameters should be managed through `config.json` or environment variables, not hardcoded.

## Git Commit Messages

- **Format:** `Type(Scope): Subject`
    - `Type`: `feat` (new feature), `fix` (bug fix), `docs` (documentation), `style` (formatting, no code change), `refactor` (refactoring code), `test` (adding tests), `chore` (maintenance).
    - `Scope`: Optional, indicates the part of the codebase affected (e.g., `audio-capture`, `api`).
    - `Subject`: Concise, imperative mood, less than 50 characters.
- **Body:** Optional, provide more detailed explanation if necessary.

```
feat(search): Implement keyword search functionality

Adds the ability to search transcribed conversations by keywords using FTS5.
```
