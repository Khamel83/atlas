#!/bin/bash
# End-to-End Test Plan: Zero-to-AI on Oracle Linux

# Objective:
# This script documents the manual steps to test the full user journey,
# from a fresh Oracle Cloud VM to a working AI environment.

# Prerequisites:
# 1. A fresh Oracle Linux VM.
# 2. An SSH connection to the VM.
# 3. A 1Password account with the `op` CLI installed locally (for setup).
# 4. A `bootstrap-env` item in the `Private` vault in 1Password, with an
#    `env` field containing a valid OPENROUTER_API_KEY.

set -e

echo "🚀 STARTING ZERO-TO-AI TEST PLAN 🚀"

# --- Step 1: One-Command Installation ---
# Description: The user runs the single installation command from the README.
# Expected: The script installs oos and all dependencies (git, python, op) automatically.

echo "
# STEP 1: Running the one-command installer...
#"
read -p "Press Enter to run the installer..."

curl -fsSL https://raw.githubusercontent.com/Khamel83/oos/master/install.sh | bash

echo "
# VERIFICATION 1: Check that 'oos', 'git', 'python3', and 'op' are installed.
#"
command -v oos
command -v git
command -v python3
command -v op

read -p "Press Enter if all commands were found..."

# --- Step 2: First Run and Guided Setup ---
# Description: The user runs `oos` in a new, empty directory.
# Expected: The script guides the user through 1Password sign-in and creates the .env file.

TEST_DIR="/tmp/oos-test-project"
echo "
# STEP 2: Running oos for the first time in a new directory ($TEST_DIR)...
#"
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

read -p "Press Enter to run oos..."

# This step is interactive. The user must follow the prompts to sign in.
oos


echo "
# VERIFICATION 2: Check that the .env file was created.
#"
ls -l .env

read -p "Press Enter if the .env file exists..."

# --- Step 3: Instant Agent Readiness ---
# Description: The user immediately tries to use an AI agent.
# Expected: The agent runner script works out-of-the-box and connects to the AI service.

# Note: This test requires a valid OpenRouter API key in the 1Password vault.
# We will run the Gemini runner and expect it to start without error.
# We can't easily script the interaction, so we'll check for the startup message.

echo "
# STEP 3: Running the Gemini agent...
#"

read -p "Press Enter to run the Gemini agent..."

# We will run the command in the background and kill it after a few seconds.
# A successful test is if the command starts without an immediate error.
.agents/runners/run_gemini.sh &>
GEMINI_PID=$!
sleep 5
kill $GEMINI_PID || true # Kill the process, ignore error if it already exited

echo "
# VERIFICATION 3: Check if the agent started successfully.
# If you saw 'Starting Gemini chat...' and no errors, the test is a success.
#"


echo "🎉 TEST PLAN COMPLETE 🎉"
echo "If all steps and verifications were successful, the project has passed the Zero-to-AI test."
