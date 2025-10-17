# Feature: Zero-to-AI Test Plan

## /specify

This document defines the end-to-end test plan to ensure the `oos` project is successful for a non-expert user on a fresh Oracle Cloud VM. The goal is to validate a seamless, one-command setup process that results in a fully functional, multi-agent AI environment.

**User Persona:**
- A user with a fresh Oracle Cloud "Always Free" VM (Oracle Linux).
- Connects via a standard SSH client.
- Has a 1Password account containing an OpenRouter API key.
- Has minimal technical knowledge.

**Success Criteria:**
1.  A single `curl | bash` command from the `README.md` installs `oos` and all its dependencies (`git`, `python3`, `unzip`, 1Password CLI).
2.  Running `oos` for the first time provides simple, clear instructions to log into 1Password.
3.  The setup automatically and securely retrieves the OpenRouter API key.
4.  Immediately after setup, the user can successfully run an agent script (e.g., `.agents/runners/run_gemini.sh`) and get a response.

## /plan

To achieve this, we will harden the `install.sh` script to be fully autonomous and create a test script to validate the entire workflow.

**Technical Approach:**
1.  **Modify `install.sh`:**
    - Add OS detection to identify Oracle Linux (or other RHEL-based systems).
    - Use `sudo dnf install -y` to automatically install `git`, `python3`, and `unzip`.
    - Add a function to download, install, and configure the 1Password CLI (`op`) from its official source.
2.  **Create Test Script `tests/test_zero_to_ai.sh`:**
    - This script will simulate the user's actions.
    - It will not be a unit test, but a full end-to-end integration test.
    - It will require manual setup of a test environment (or be run in a clean VM).
    - The script will perform the installation, run the setup, and attempt to use an agent, checking the output at each stage.

## /tasks

- **T001**: Refactor `install.sh` to add OS detection and automatic installation of `git`, `python3`, and `unzip` using the appropriate package manager (`dnf` for Oracle Linux).
- **T002**: Add a new function to `install.sh` to automatically download the 1Password CLI RPM, install it, and clean up the downloaded file.
- **T003**: Refactor the main `run.py` script to improve the clarity and simplicity of the prompts during the first-run setup process.
- **T004**: Create a new test script `tests/test_zero_to_ai.sh` that contains the step-by-step commands to execute the full "Zero-to-AI" user journey.
- **T005**: Manually execute the `tests/test_zero_to_ai.sh` script in a suitable environment and document its successful execution, confirming the project passes the test.
