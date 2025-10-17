# Atlas Standards: Code Style

This document outlines the code style guidelines for the Atlas project. Adhering to these guidelines ensures consistency, readability, and maintainability across the codebase.

## General Principles

- **Readability**: Code should be easy to read and understand.
- **Consistency**: Follow existing patterns and conventions within the project.
- **Clarity**: Avoid overly clever or obscure code.

## Python Specific

- **PEP 8**: Adhere to PEP 8, the Python style guide, for all Python code.
- **Black**: Use Black as an uncompromising code formatter to ensure consistent formatting.
- **Flake8**: Use Flake8 for linting to enforce style guide adherence and catch common errors.

## Naming Conventions

- **Variables and Functions**: `snake_case`
- **Classes**: `CamelCase`
- **Constants**: `UPPER_SNAKE_CASE`

## Comments and Documentation

- **Docstrings**: Use Google-style docstrings for modules, classes, methods, and functions.
- **Inline Comments**: Use sparingly, only for explaining complex logic or non-obvious decisions.

## Imports

- Organize imports according to PEP 8 (standard library, third-party, local application).
- Use `isort` to automatically sort imports.

## Example (Python)

```python
def calculate_total(price: float, quantity: int) -> float:
    """
    Calculates the total price of an item.

    Args:
        price: The price per unit.
        quantity: The number of units.

    Returns:
        The total price.
    """
    return price * quantity
```
