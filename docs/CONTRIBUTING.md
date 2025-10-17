# Contributing to Atlas

First off, thank you for considering contributing to Atlas! It's people like you that make Atlas such a great tool for personal knowledge management.

Following these guidelines helps to communicate that you respect the time of the developers managing and developing this open source project. In return, they should reciprocate that respect in addressing your issue, assessing changes, and helping you finalize your pull requests.

## Code of Conduct

This project and everyone participating in it is governed by the [Atlas Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [conduct@atlas-platform.com](mailto:conduct@atlas-platform.com).

## What We're Looking For

Atlas is always looking for contributions in the following areas:

### Documentation
- Improving existing documentation
- Writing new guides and tutorials
- Creating video tutorials
- Translating documentation to other languages
- Updating API documentation

### Code Contributions
- Bug fixes
- Performance improvements
- New features
- Integration with new services
- Mobile app enhancements

### Testing
- Writing unit tests
- Writing integration tests
- Reporting bugs
- Verifying bug fixes

### Community
- Answering questions in forums
- Helping with user support
- Creating educational content
- Speaking at conferences and meetups

## What We're NOT Looking For

To ensure a smooth contribution process, please avoid:

- **Breaking changes** without prior discussion
- **Major refactoring** without prior agreement
- **Unrelated features** that don't align with Atlas's mission
- **Pull requests** without associated issues (for significant changes)

## Getting Started

### Prerequisites
Before you begin, ensure you have the following installed:
- Python 3.9 or higher
- Git
- Virtual environment tool (venv or conda)

### Setting Up Your Development Environment
1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/atlas.git
   cd atlas
   ```
3. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
6. Run initial setup:
   ```bash
   python scripts/setup_wizard.py --automated
   ```

### Code Structure
Understanding Atlas's code structure is crucial for effective contributions:

```
atlas/
├── api/                 # FastAPI REST endpoints
├── ask/                 # Cognitive amplification modules
├── helpers/             # Utility functions and managers
├── ingest/              # Content ingestion pipelines
├── web/                 # Web dashboard and frontend
├── mobile/              # Mobile integration
├── scripts/             # Utility and setup scripts
├── tests/               # Unit and integration tests
├── docs/                # Documentation
├── config/              # Configuration files
├── logs/                # Log files
├── output/              # Processed content
└── venv/                # Virtual environment (git ignored)
```

## How to Contribute

### Reporting Bugs

This section guides you through submitting a bug report for Atlas. Following these guidelines helps maintainers and the community understand your report, reproduce the behavior, and find related reports.

**Before Submitting A Bug Report**
- Check the [existing issues](https://github.com/your-username/atlas/issues) to see if the problem has already been reported
- Check if the issue has been fixed by trying to reproduce it using the latest `main` branch in the repository

**How Do I Submit A (Good) Bug Report?**
Bugs are tracked as [GitHub issues](https://guides.github.com/features/issues/). Create an issue and provide the following information by filling in [the template](ISSUE_TEMPLATE/bug_report.md).

Explain the problem and include additional details to help maintainers reproduce the problem:

- **Use a clear and descriptive title** for the issue
- **Describe the exact steps** which reproduce the problem
- **Provide specific examples** to demonstrate the steps
- **Describe the behavior you observed** after following the steps
- **Explain which behavior you expected** to see instead
- **Include screenshots** which show you following the described steps
- **Include copies of configuration files** if relevant
- **Include the version of Atlas** you're using
- **Include your operating system** name and version

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion for Atlas, including completely new features and minor improvements to existing functionality.

**Before Submitting An Enhancement Suggestion**
- Check the [existing issues](https://github.com/your-username/atlas/issues) to see if the enhancement has already been suggested
- Check if the enhancement is already planned in the [roadmap](docs/PROJECT_ROADMAP.md)

**How Do I Submit A (Good) Enhancement Suggestion?**
Enhancement suggestions are tracked as [GitHub issues](https://guides.github.com/features/issues/). Create an issue and provide the following information by filling in [the template](ISSUE_TEMPLATE/feature_request.md):

- **Use a clear and descriptive title** for the issue
- **Provide a step-by-step description** of the suggested enhancement
- **Provide specific examples** to demonstrate the steps
- **Describe the current behavior** and **explain which behavior you expected** to see instead
- **Include screenshots** which help you demonstrate the steps or point out the part of Atlas which the suggestion is related to
- **Explain why this enhancement would be useful** to most Atlas users
- **Specify which version of Atlas** you're using
- **Specify the operating system** you're using

### Your First Code Contribution

Unsure where to begin contributing to Atlas? You can start by looking through these `beginner` and `help-wanted` issues:

- [Beginner issues][beginner] - issues which should only require a few lines of code, and a test or two.
- [Help wanted issues][help-wanted] - issues which should be a bit more involved than `beginner` issues.

Both issue lists are sorted by total number of comments. While not perfect, number of comments is a reasonable proxy for impact a given change will have.

### Pull Requests

The process described here has several goals:

- Maintain Atlas's quality
- Fix problems that are important to users
- Engage the community in working toward the best possible Atlas
- Enable a sustainable system for Atlas's maintainers to review contributions

Please follow these steps to have your contribution considered by the maintainers:

1. Follow all instructions in [the template](PULL_REQUEST_TEMPLATE.md)
2. Follow the [style guides](#style-guides)
3. After you submit your pull request, verify that all [status checks](https://help.github.com/articles/about-status-checks/) are passing

While the prerequisites above must be satisfied prior to having your pull request reviewed, the reviewer(s) may ask you to complete additional design work, tests, or other changes before your pull request can be ultimately accepted.

## Style Guides

### Git Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line
- When only changing documentation, include `[ci skip]` in the commit title
- Consider starting the commit message with an applicable emoji:
  - :rocket: `:rocket:` when releasing a new version
  - :sparkles: `:sparkles:` when introducing new features
  - :bug: `:bug:` when fixing a bug
  - :memo: `:memo:` when writing docs
  - :rotating_light: `:rotating_light:` when removing linter warnings
  - :white_check_mark: `:white_check_mark:` when adding tests
  - :arrow_up: `:arrow_up:` when upgrading dependencies
  - :arrow_down: `:arrow_down:` when downgrading dependencies
  - :shirt: `:shirt:` when removing linter warnings

### Python Style Guide

Atlas follows [PEP 8](https://www.python.org/dev/peps/pep-0008/) with some additional conventions:

- Use 4 spaces for indentation (not tabs)
- Maximum line length is 88 characters (following Black formatter)
- Use double quotes for strings
- Use underscores for variable and function names (snake_case)
- Use PascalCase for class names
- Use descriptive variable names
- Write docstrings for all public modules, functions, classes, and methods
- Use type hints where appropriate

### Documentation Style Guide

- Use Markdown for documentation files
- Use sentence case for headers (not title case)
- Keep line lengths to 80 characters where possible
- Use descriptive link text (not "click here")
- Use present tense ("Click the button" not "Clicked the button")
- Use active voice ("The system processes the request" not "The request is processed by the system")

## Additional Notes

### Issue and Pull Request Labels

This section lists the labels we use to help us track and manage issues and pull requests.

[GitHub search](https://help.github.com/articles/searching-issues/) makes it easy to use labels for finding groups of issues or pull requests you're interested in. For example, you might be interested in [open issues across `atlas` that are labeled as bugs, but still need to be reproduced](https://github.com/your-username/atlas/issues?q=is%3Aopen+is%3Aissue+label%3Abug+label%3Aneeds-reproduction), or perhaps [open pull requests in `atlas` that haven't been reviewed yet](https://github.com/your-username/atlas/pulls?q=is%3Aopen+is%3Apr+review%3Anone). To help you find issues and pull requests, each label is listed with search links for finding open items with that label. We encourage you to read about [other search filters](https://help.github.com/articles/searching-issues/) which will help you write more focused queries.

The labels are loosely grouped by their purpose, but it's not required that every issue have a label from every group or that an issue can't have more than one label from the same group.

Please open an issue on `atlas` if you have suggestions for new labels, and if you notice some labels are missing on some repositories, then please open an issue on that repository.

## Community Participation

### Forums and Chat

Join our community to discuss Atlas, get help, and contribute ideas:

- **Discord**: https://discord.gg/atlas
- **Reddit**: r/AtlasPlatform
- **GitHub Discussions**: https://github.com/your-username/atlas/discussions

### Events

We host regular community events:

- **Monthly Community Calls**: First Tuesday of each month
- **Hackathons**: Quarterly virtual hackathons
- **Workshops**: Occasional workshops on specific topics

Check our [events calendar](https://atlas-platform.com/events) for upcoming events.

### Recognition

We recognize and celebrate contributions through:

- **Contributor Spotlight**: Monthly feature of outstanding contributors
- **Swag Program**: Send swag to active contributors
- **Conference Speaking**: Invite contributors to speak at conferences
- **Employment Opportunities**: Help contributors find jobs in related fields

## Conclusion

Atlas thrives on community contributions. Whether you're fixing a typo, writing documentation, or adding new features, your efforts are appreciated and valued.

Thank you for being part of the Atlas community! 🚀🧠