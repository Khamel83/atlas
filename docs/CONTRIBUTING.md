# 🎯 Contributing & Development

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
