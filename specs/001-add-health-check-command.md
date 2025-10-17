# Feature: Add Health Check Command

## /specify

Add a new `health` command to the main `run.py` script. This command will perform a simple health check of the OOS environment. The purpose is to provide a quick way for users to verify that their local setup is correct and that the core dependencies are available.

**Success Criteria:**
- Running `python3 run.py health` should execute the health check.
- The health check should verify the existence and versions of `python`, `git`, and `op` (1Password CLI).
- It should print a simple, human-readable report to the console.
- If a check passes, it should print `[OK]`. If it fails, it should print `[FAIL]` with a brief error message.
- The command should exit with status 0 if all checks pass, and 1 otherwise.

## /plan

The implementation will be done within the existing `run.py` script, following the pattern of other commands. No new files or dependencies are needed.

**Tech Stack:**
- Python 3 (using the `subprocess` and `shutil` modules)

**Architecture:**
- Add a new `elif` block to the main execution section of `run.py` to handle the `health` argument.
- Create a new function, `run_health_check()`, within `run.py` to contain the health check logic.
- The `run_health_check()` function will use `shutil.which()` to check for the existence of the required executables.

## /tasks

- **T001**: Modify `run.py` to add a new function `run_health_check()`. This function will contain the logic for checking `python`, `git`, and `op`.
- **T002**: Modify the main execution block in `run.py` to call `run_health_check()` when the first argument is `health`.
- **T003**: Add a new test file `tests/test_health_check.py` to specifically test the `run_health_check` command and its output.
