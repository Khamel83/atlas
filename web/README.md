# Atlas Web Interface for Scheduling

This directory contains the web-based management interface for Atlas scheduled jobs.

## Features
- View all scheduled jobs (table view)
- Add new jobs (name, cron string)
- Edit job schedule (cron string)
- Enable/disable jobs
- Delete jobs
- Manually trigger jobs
- View job logs (in-memory for custom jobs, real log files for article, podcast, and YouTube ingestion jobs)
- **Last run status and time for ingestion jobs**: The jobs table now shows the last run status (success/error) and timestamp for each ingestion job.
- **User feedback and error handling:** UI displays success/error messages for all actions, including invalid cron strings

## Tech Stack
- Backend: FastAPI (Python)
- Frontend: Jinja2 templates (MVP), upgradeable to React
- Database: SQLite (APScheduler job store)

## Troubleshooting

- If you see `zsh: command not found: uvicorn`, install it with:
  ```bash
  pip install uvicorn
  ```
- Ensure `uvicorn` is available in your PATH to run the web UI.

## Usage

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install uvicorn  # Ensure uvicorn is installed
   ```
2. **Run the web app:**
   ```bash
   uvicorn web.app:app --reload
   ```
3. **Open in browser:**
   - Go to [http://localhost:8000/jobs/html](http://localhost:8000/jobs/html)

## Error Handling & User Feedback
- The UI displays clear success and error messages for all actions (add, edit, enable/disable, delete, trigger, logs)
- Invalid cron strings are caught and reported to the user
- All major features are now implemented and the interface is ready for use

## Notes
- The web interface and main scheduler both use the same SQLite job store: `scheduler.db` in the project root.
- This ensures robust job persistence and recovery: jobs will survive restarts and are shared between the CLI, daemon, and web UI.
- Do not delete `scheduler.db` if you want to preserve your scheduled jobs.
- **Ingestion job logs (articles, podcasts, YouTube) are now displayed in the web UI, pulled directly from their respective log files.**
- Job logs for custom jobs are stored in memory and will be lost on restart (MVP).
- Adding/editing jobs currently uses a dummy function for demonstration.

## Roadmap
- Improve error handling and validation
- Persist logs to disk or database
- Add authentication
- Upgrade to React frontend (optional)

---

*This README will be updated as the web interface evolves.*
