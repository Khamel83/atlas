Here is a detailed guide on what I would need to achieve a 100% success rate on your tasks:

  1. The Ideal Task Definition

  The way you define a task is the most critical factor. I don't have intuition or implicit
  understanding, so my performance is directly proportional to the clarity of your instructions.

   * Atomicity: Break down large goals into the smallest possible subtasks. Each task should represent
     a single, logical unit of work.
       * Instead of: "Implement user authentication."
       * Do this:
           1. "Create a new database migration to add a users table with id, email, and password_hash
              columns."
           2. "Create a /register endpoint that takes an email and password, hashes the password, and
              saves a new user to the database."
           3. "Write a unit test for the /register endpoint that verifies a user is created
              successfully."

   * Explicitness and Unambiguity: Leave no room for interpretation.
       * Instead of: "Fix the bug on the dashboard."
       * Do this: "When a user with no projects clicks the 'Dashboard' link, the application crashes.
          It should instead display the 'empty_dashboard' component located at
         `src/components/empty_dashboard.js`."

   * Clear Acceptance Criteria: Define what "done" means in a verifiable way.
       * Instead of: "The API should be fast."
       * Do this: "The GET /api/v1/items endpoint must return a response in under 100ms with a 99%
         success rate under a load of 50 concurrent users."

   * Reference Existing Patterns: If the new code should follow an existing pattern, point me to it
     directly.
       * Do this: "Create a new ProductService that follows the same singleton pattern and method
         structure as the UserService in src/services/user.service.py."

  2. The Ideal Project Environment

  My ability to execute code depends entirely on the environment you provide.

   * Automated Setup: The project should have a script (setup.sh, scripts/install.sh) or a container
     definition (Dockerfile, docker-compose.yml) that installs all required dependencies, tools, and
     language runtimes. This ensures I have the tools I need, like ffmpeg or psql, available in the
     shell.
   * Configuration Management: All configuration, especially secrets, should be loaded from
     environment variables or a .env file. The task description should specify which environment
     variables are required to run the code. I cannot and will not handle raw secrets.
   * A Comprehensive `README.md`: This file is my entry point. It should contain:
       * A brief description of the project.
       * Clear, step-by-step instructions on how to set up the development environment.
       * Commands to run the application, run tests, and run the linter.

  3. The Ideal Codebase

  The structure and quality of the existing code directly impact how quickly and reliably I can
  make changes.

   * A Strong Test Suite: This is the single most important factor for speed and reliability. A
     comprehensive test suite (unit, integration, and E2E tests) allows me to:
       * Understand the expected behavior of the code.
       * Verify that my changes have the intended effect.
       * Ensure that I have not introduced any regressions.
      With a good test suite, I can work much more autonomously and confidently.
   * Consistent Code Style: A linter (like Ruff, Prettier, or ESLint) and a code formatter should be
     configured and enforced. This makes the code predictable and easier for me to parse and modify.
   * Modularity: A modular codebase with a clear separation of concerns allows me to work on one
     component without needing to understand the entire system.

  How This Leads to Fewer Tokens and Faster Execution

  Following these guidelines directly translates to higher efficiency:

   * Reduced Back-and-Forth: Clear, atomic tasks with acceptance criteria eliminate the need for me
     to ask clarifying questions, which is a major source of token consumption and delay.
   * Less Context Loading: When you point me to the exact files and patterns to use, I don't have to
     spend tokens and time reading through the entire codebase to find the relevant context.
   * Higher Success Rate: A strong test suite allows me to validate my own work and correct my
     mistakes instantly, without needing your intervention. This "self-correction" loop is much
     faster and more token-efficient than a feedback loop that involves you.

  In essence, the more you can treat me like a very fast, very literal junior developer who needs
  explicit instructions and a solid testing framework, the better I will perform. By setting up the
   tasks and the environment in this way, you are programming me for success.