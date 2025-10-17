# Contributing to OOS

Thank you for your interest in contributing to OOS! This guide covers both using OOS in your projects and contributing to the OOS project itself.

## 🚀 Using OOS (Most Users)

If you want to use OOS in your project:
```bash
curl -sSL https://raw.githubusercontent.com/Khamel83/oos/master/install.sh | bash
```

See [README.md](README.md) for usage instructions.

## 🔧 Contributing to OOS Development

This section is for developers working **on** the OOS project itself.

### 1. Environment Setup

**Prerequisite: `uv`**

This project uses `spec-kit`, which requires `uv`. If you don't have it installed, run the following command:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

To set up your development environment, clone the repository and run the bootstrap script. This will install all required dependencies, including development tools.

```bash
# Clone the repository
git clone https://github.com/Khamel83/oos.git
cd oos

# Run the development bootstrap script
./scripts/bootstrap_enhanced.sh
```

### 2. Running the Test Suite

This project uses `pytest` for testing. To run the entire test suite, use the following command:

```bash
# Run all tests
./bin/run_tests.sh
```

### 3. Linting and Formatting

We use `Ruff` for linting and `Black` for formatting.

```bash
# Check for linting errors
ruff check .

# Automatically fix linting errors
ruff check . --fix

# Format code with Black
black .
```

### 4. Our Development Process (Spec-Driven)

All new features and changes are guided by a specification. We use `spec-kit` to ensure changes are well-defined before implementation.

1.  **Create a Spec:** Write a new `.md` file in the `/specs` directory.
2.  **Define the Work:** Use the `/specify`, `/plan`, and `/tasks` commands within your spec to detail the what, how, and the exact steps for implementation.
3.  **Implement:** Execute the tasks defined in the spec.

For a complete guide on our collaboration principles, see the [AI Collaboration Guide](docs/AI_COLLABORATION.md).

## 🎯 General Contribution Guidelines

### 🐛 Bug Reports
- Use the [issue tracker](https://github.com/Khamel83/oos/issues)
- Include steps to reproduce the issue
- Mention your OS and project type
- Include error messages and relevant logs

### ✨ Feature Requests
- Open an issue with the "enhancement" label
- Describe the use case and benefits
- Consider backward compatibility with existing installations

### 📝 Pull Requests
1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes following our coding standards
4. Test thoroughly with `./test_production.sh`
5. Update documentation if needed
6. Submit a pull request with clear description

### 🧪 Testing Production Changes
Before submitting any changes that affect the installer or core functionality:

```bash
# Run the production test suite
./test_production.sh

# Test the installer end-to-end
cd /tmp && mkdir test-oos && cd test-oos
curl -sSL https://raw.githubusercontent.com/Khamel83/oos/master/install.sh | bash
./oos search "test query"
```

### 🔒 Security
- Never commit API keys or secrets
- Review security scan results before committing
- Test with invalid/expired keys
- Follow responsible disclosure for security issues

## 🤝 Community Guidelines
- Be respectful and welcoming to newcomers
- Provide constructive feedback
- Focus on practical solutions that help users
- Keep discussions technical and objective

## 🎉 Recognition
Contributors are recognized in release notes and the project README. Thank you for helping make OOS better for everyone! 🚀
