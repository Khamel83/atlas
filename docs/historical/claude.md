# Claude — Model Specifics

Use this file only for Claude-specific behavior. The execution lifecycle is in `agents.md`.

## Runtime Notes
- Good at code edits and doc rewrites; use for larger refactors when precision matters.
- Prefer smaller, iterative diffs with clear commit messages.

## Settings (suggested)
- Temperature: low for code; moderate for prose rewrites.
- Max tokens: ensure room for diff + file context.

## Known Quirks
- May over-explain; keep it concise and structured.
