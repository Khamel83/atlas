# OOS Usage Guide

This guide shows you how to use the `oos` command for common tasks.

## The `oos` Command

The `oos` command is interactive and will guide you through the process of setting up your project. Just run it in your project directory and it will ask you what you want to do.

```bash
# Navigate to your project directory
cd /path/to/my-project

# Run oos
oos
```

## Common Scenarios

### Scenario 1: Starting a New Project

If you run `oos` in an empty directory, it will help you create a new project.

1.  Create a new directory and navigate into it:
    ```bash
    mkdir my-new-app
    cd my-new-app
    ```
2.  Run `oos`:
    ```bash
    oos
    ```
3.  Follow the prompts to choose the type of project you want to create.

### Scenario 2: Adding OOS to an Existing Project

If you run `oos` in a directory that already has a project, it will help you add OOS features to it.

1.  Navigate to your existing project directory:
    ```bash
    cd /path/to/my-existing-app
    ```
2.  Run `oos`:
    ```bash
    oos
    ```
3.  Follow the prompts to add features like secure environment management.

## Getting Help

If you ever need help, you can run `oos --help` to see a list of available commands and options.

```bash
oos --help
```
