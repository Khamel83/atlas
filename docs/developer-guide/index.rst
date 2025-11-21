Developer Guide
===============

Welcome to Atlas development! This guide will help you get started contributing to the Atlas project.

.. toctree::
   :maxdepth: 2

   getting-started
   architecture
   testing
   code-standards
   contribution-process

Quick Start
-----------

Get up and running with Atlas development in minutes:

.. code-block:: bash

   # Clone and setup
   git clone https://github.com/atlas/atlas.git
   cd atlas
   
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Setup pre-commit hooks
   pre-commit install
   
   # Run tests to verify setup
   python tests/run_tests.py quick
   
   # Start Atlas
   ./start_work.sh

Development Environment
-----------------------

Required Tools
~~~~~~~~~~~~~~

- **Python 3.12+**: Primary development language
- **Git**: Version control and collaboration
- **pytest**: Testing framework
- **pre-commit**: Code quality automation
- **Sphinx**: Documentation generation

Optional but Recommended
~~~~~~~~~~~~~~~~~~~~~~~~

- **Docker**: Container development and deployment
- **VS Code**: With Python and Atlas extensions
- **pytest-xdist**: Parallel test execution
- **ruff**: Fast Python linting

Project Structure
-----------------

Understanding Atlas's architecture:

.. code-block:: text

   atlas/
   ├── helpers/              # Core processing modules
   │   ├── article_ingestor.py
   │   ├── podcast_ingestor.py
   │   ├── metadata_manager.py
   │   └── utils.py
   ├── process/              # Content processing
   ├── ask/                  # Cognitive features
   ├── modules/              # Extension modules
   ├── tests/                # Comprehensive test suite
   ├── docs/                 # Documentation
   ├── scripts/              # Development utilities
   └── config/               # Configuration files

Development Workflow
--------------------

1. **Issue Assignment**
   
   - Check GitHub issues for tasks
   - Comment to request assignment
   - Create branch: ``feature/issue-number-description``

2. **Development Process**
   
   .. code-block:: bash
   
      # Create feature branch
      git checkout -b feature/123-improve-search
      
      # Make changes with frequent commits
      git add .
      git commit -m "Add semantic search capability"
      
      # Run tests frequently
      python tests/run_tests.py quick
      
      # Pre-commit hooks run automatically
      git push origin feature/123-improve-search

3. **Code Review**
   
   - Create pull request with description
   - Ensure all CI checks pass
   - Address review feedback
   - Squash commits if needed

Code Quality Standards
----------------------

Formatting and Style
~~~~~~~~~~~~~~~~~~~~

Atlas follows strict code quality standards enforced by pre-commit hooks:

- **Black**: Code formatting (88 characters)
- **isort**: Import sorting
- **Ruff**: Fast linting and error checking
- **MyPy**: Type checking for critical modules

Documentation Requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~

All public functions must include comprehensive docstrings:

.. code-block:: python

   def process_article(url: str, config: Dict[str, Any]) -> Dict[str, Any]:
       """
       Process an article from URL with comprehensive metadata extraction.
       
       This function handles the complete article processing pipeline including
       content fetching, metadata extraction, and result storage.
       
       Args:
           url (str): Article URL to process
           config (Dict[str, Any]): Configuration dictionary with settings
           
       Returns:
           Dict[str, Any]: Processing results with metadata and content
           
       Raises:
           ValueError: If URL is invalid
           ConnectionError: If article cannot be fetched
           
       Example:
           >>> config = load_config()
           >>> result = process_article("https://example.com/article", config)
           >>> print(result['success'])
           True
       """

Testing Requirements
~~~~~~~~~~~~~~~~~~~~

Every contribution must include appropriate tests:

- **Unit tests**: For individual functions and classes
- **Integration tests**: For component interactions
- **Performance tests**: For optimization work
- **Security tests**: For security-related changes

.. code-block:: python

   @pytest.mark.unit
   def test_process_article_success(self):
       """Test successful article processing."""
       # Test implementation
       
   @pytest.mark.integration  
   def test_full_pipeline_integration(self):
       """Test complete processing pipeline."""
       # Integration test implementation

Running Tests
~~~~~~~~~~~~~

Atlas provides multiple testing modes:

.. code-block:: bash

   # Quick unit tests only
   python tests/run_tests.py quick
   
   # Full test suite with coverage
   python tests/run_tests.py full
   
   # Performance tests
   python tests/run_tests.py performance
   
   # Security tests
   python tests/run_tests.py security
   
   # Integration tests
   python tests/run_tests.py integration

Common Development Tasks
------------------------

Adding a New Ingestor
~~~~~~~~~~~~~~~~~~~~~

1. Create ingestor class inheriting from ``BaseIngestor``
2. Implement required methods: ``process_urls()``, ``get_content_type()``
3. Add comprehensive unit tests
4. Update documentation
5. Add integration tests

Example structure:

.. code-block:: python

   from helpers.base_ingestor import BaseIngestor
   from helpers.metadata_manager import ContentType
   
   class NewIngestor(BaseIngestor):
       """Ingestor for new content type."""
       
       def get_content_type(self):
           return ContentType.NEW_TYPE
           
       def process_urls(self, urls: List[str]) -> Dict[str, Any]:
           """Process URLs for new content type."""
           # Implementation here

Adding New Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

1. Add to ``helpers/config.py`` with environment variable
2. Update ``env.template`` with documentation
3. Add validation in ``load_config()``
4. Add tests for new configuration

.. code-block:: python

   # In config.py
   config = {
       "new_setting": os.getenv("NEW_SETTING", "default_value"),
       # ... other config
   }

Building Documentation
~~~~~~~~~~~~~~~~~~~~~~

Atlas uses Sphinx for documentation:

.. code-block:: bash

   # Build documentation
   cd docs
   make dev-docs
   
   # Serve locally
   make serve
   
   # Check for issues
   make check

Debugging and Troubleshooting
------------------------------

Common Issues
~~~~~~~~~~~~~

**Import Errors**
   - Check virtual environment is activated
   - Verify all dependencies installed: ``pip install -r requirements.txt``

**Test Failures**
   - Run specific failing test: ``pytest tests/unit/test_failing.py -v``
   - Check test environment setup in ``conftest.py``

**Pre-commit Hook Failures**
   - Run hooks manually: ``pre-commit run --all-files``
   - Fix reported issues before committing

**Documentation Build Errors**
   - Check for syntax errors in docstrings
   - Verify all imports are available
   - Run: ``sphinx-build -b html . _build/html``

Development Tools
~~~~~~~~~~~~~~~~~

**Debugging**

.. code-block:: python

   import logging
   logging.basicConfig(level=logging.DEBUG)
   
   # Or use built-in debugging
   from helpers.utils import setup_logging
   setup_logging("/tmp/atlas_debug.log")

**Performance Profiling**

.. code-block:: python

   import cProfile
   import pstats
   
   # Profile function
   cProfile.run('your_function()', 'profile_stats')
   stats = pstats.Stats('profile_stats')
   stats.sort_stats('cumulative').print_stats(10)

Contributing Guidelines
-----------------------

Pull Request Process
~~~~~~~~~~~~~~~~~~~~

1. **Before Starting**
   
   - Discuss large changes in GitHub issues first
   - Check for existing similar work
   - Ensure you understand the requirements

2. **Pull Request Description**
   
   - Clear title describing the change
   - Detailed description of what was changed and why
   - Link to related issues
   - Screenshots for UI changes
   - Performance impact for optimization work

3. **Review Process**
   
   - All CI checks must pass
   - At least one code review required
   - Documentation must be updated for API changes
   - Tests must be included for new functionality

Code Review Checklist
~~~~~~~~~~~~~~~~~~~~~~

Reviewers should verify:

- ✅ Code follows Atlas style guidelines
- ✅ Comprehensive tests included
- ✅ Documentation updated appropriately  
- ✅ Security considerations addressed
- ✅ Performance impact considered
- ✅ Error handling implemented
- ✅ Backward compatibility maintained

Release Process
~~~~~~~~~~~~~~~

Atlas follows semantic versioning:

- **Major (x.0.0)**: Breaking changes
- **Minor (0.x.0)**: New features, backward compatible
- **Patch (0.0.x)**: Bug fixes, backward compatible

Community
---------

Getting Help
~~~~~~~~~~~~

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and community discussion
- **Documentation**: Comprehensive guides and API reference

Contributing Areas
~~~~~~~~~~~~~~~~~~

Looking to contribute? Areas that need help:

- 🧪 **Testing**: Expand test coverage, performance tests
- 📚 **Documentation**: Tutorials, examples, API docs  
- 🔧 **Tools**: Development utilities, CI/CD improvements
- 🚀 **Features**: New ingestors, search improvements
- 🐛 **Bug Fixes**: Issue triage and resolution
- 🔒 **Security**: Vulnerability assessment, hardening

Recognition
~~~~~~~~~~~

Contributors are recognized in:

- Release notes for their contributions
- ``CONTRIBUTORS.md`` file
- Annual contributor appreciation

Next Steps
----------

Ready to contribute? Start here:

1. **First Contribution**: Look for "good first issue" labels
2. **Documentation**: Help improve guides and examples
3. **Testing**: Add tests for existing functionality
4. **Features**: Propose and implement new capabilities

Thank you for contributing to Atlas! 🚀