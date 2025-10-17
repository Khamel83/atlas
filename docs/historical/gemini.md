# Gemini — Model Specifics

Use this file only for Gemini-specific behavior. The execution lifecycle is in `agents.md`.

## Runtime Notes
- Strong at structured planning and following rigid templates.
- Keep instructions single-shot and fully specified (this brief).

## Settings (suggested)
- Deterministic settings for repeatable file writes.
- Ensure context includes the exact file payloads to avoid drift.

## Known Quirks
- Can truncate outputs on very long generations. Prefer per-file commits if needed.
