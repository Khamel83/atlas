"""
Sphinx configuration file for Atlas API documentation.

This file configures Sphinx to generate comprehensive API documentation
from the Atlas codebase, including docstrings, examples, and cross-references.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "helpers"))
sys.path.insert(0, str(project_root / "process"))
sys.path.insert(0, str(project_root / "ask"))
sys.path.insert(0, str(project_root / "modules"))

# -- Project information -----------------------------------------------------

project = 'Atlas'
copyright = '2024, Atlas Development Team'
author = 'Atlas Development Team'
version = '1.0.0'
release = '1.0.0'

# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',          # Automatic documentation from docstrings
    'sphinx.ext.autosummary',      # Generate autodoc summaries
    'sphinx.ext.viewcode',         # Add source code links
    'sphinx.ext.napoleon',         # Support for NumPy and Google style docstrings
    'sphinx.ext.intersphinx',      # Link to other projects' documentation
    'sphinx.ext.todo',             # Support for todo items
    'sphinx.ext.coverage',         # Check documentation coverage
    'sphinx.ext.doctest',          # Test code examples in docstrings
    'myst_parser',                 # Support for Markdown files
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = [
    '_build',
    'Thumbs.db',
    '.DS_Store',
    'venv',
    '__pycache__',
    '*.pyc'
]

# The master toctree document
master_doc = 'index'

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages
html_theme = 'furo'

html_theme_options = {
    "sidebar_hide_name": True,
    "light_logo": "atlas-logo-light.png",
    "dark_logo": "atlas-logo-dark.png",
    "source_repository": "https://github.com/atlas/atlas",
    "source_branch": "main",
    "source_directory": "docs/",
}

html_title = "Atlas Documentation"
html_short_title = "Atlas"

# Add any paths that contain custom static files (such as style sheets)
html_static_path = ['_static']

# Custom CSS files
html_css_files = [
    'custom.css',
]

# -- Extension configuration -------------------------------------------------

# Napoleon settings for Google/NumPy docstring styles
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# Automatically extract typehints
autodoc_typehints = 'description'
autodoc_typehints_description_target = 'documented'

# Autosummary settings
autosummary_generate = True
autosummary_generate_overwrite = True

# Intersphinx configuration - link to external documentation
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'requests': ('https://docs.python-requests.org/en/master/', None),
    'beautifulsoup4': ('https://www.crummy.com/software/BeautifulSoup/bs4/doc/', None),
    'pytest': ('https://docs.pytest.org/en/stable/', None),
}

# Todo extension settings
todo_include_todos = True

# -- Custom configuration ---------------------------------------------------

# Add module-specific configurations
sys.modules['helpers'] = sys.modules.get('helpers', type(sys)('helpers'))
sys.modules['process'] = sys.modules.get('process', type(sys)('process'))
sys.modules['ask'] = sys.modules.get('ask', type(sys)('ask'))

# Mock external dependencies that might not be available during doc build
autodoc_mock_imports = [
    'playwright',
    'skyvern',
    'litellm',
    'openai',
    'meilisearch',
]

# Custom roles for Atlas-specific documentation
rst_prolog = """
.. |project| replace:: Atlas
.. |version| replace:: 1.0.0
"""

# Code highlighting
pygments_style = 'sphinx'
highlight_language = 'python3'

# -- Custom directives ------------------------------------------------------

def setup(app):
    """Custom Sphinx setup function."""
    app.add_css_file('custom.css')
    return {
        'version': '1.0.0',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }