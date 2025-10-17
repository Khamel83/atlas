# Feature: Hardening and Efficiency Improvements

## /specify

This specification outlines three major improvements to the OOS project:
1.  **Security Hardening:** Prevent the API key from ever being exposed to the agent process.
2.  **Streamlined Integration:** Create a simple, one-command method for integrating `oos` into an existing project.
3.  **Efficient Code Context:** Create a searchable manifest of the codebase to reduce expensive file system searches and improve AI context.

## /plan

### 1. Secure Execution Wrapper
- A new script, `bin/secure_exec`, will be created.
- This script will be responsible for retrieving the API key from 1Password.
- It will then execute a given command (e.g., `gemini chat`), injecting the API key directly into the child process's environment.
- The existing runner scripts (`.agents/runners/*.sh`) will be modified to use this secure wrapper instead of sourcing the `.env` file directly.

### 2. Project Integration Command
- A new command, `oos --integrate`, will be added to `run.py`.
- This command will be non-interactive and will perform the following actions:
    - Copy the `spec-kit` scaffolding (`/specs`, `/memory`, `.gemini`, etc.) into the current directory.
    - Create or update the `.gitignore` file.
    - Add development dependencies (`ruff`, `black`, `pytest`) to `requirements-dev.txt`.
    - Provide the user with instructions to run the 1Password setup.

### 3. Code Manifest
- A new script, `bin/generate_code_manifest.sh`, will be created.
- This script will use `tree` and `grep` to scan the codebase and generate a `CODE_MANIFEST.md` file.
- The manifest will contain the file structure, a list of all functions and classes, and a list of all `TODO`/`FIXME` comments.
- The `bootstrap_enhanced.sh` script will be updated to include this script.

## /tasks

- **T001**: Create the `bin/secure_exec` script with the logic to retrieve the API key from 1Password and execute a child process with the key in its environment.
- **T002**: Modify the agent runner scripts (`run_gemini.sh`, `run_claude.sh`, `run_qwen.sh`) to use `bin/secure_exec` instead of sourcing the environment directly.
- **T003**: Implement the `oos --integrate` command in `run.py`.
- **T004**: Create the `bin/generate_code_manifest.sh` script.
- **T005**: Update `bootstrap_enhanced.sh` to include the `generate_code_manifest.sh` script.
- **T006**: Run the manifest generation script and verify the `CODE_MANIFEST.md` file is created correctly.
