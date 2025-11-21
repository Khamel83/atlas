# Qwen — Model Specifics

Use this file only for Qwen-specific behavior. The execution lifecycle is in `agents.md`.

## Runtime Notes
- Fast and cheap for mechanical edits and search/replace operations.
- Use for bulk formatting and mass spec normalizations.

## Settings (suggested)
- Low temperature; smaller context windows per operation.

## Known Quirks
- Watch for encoding/whitespace drift. Run formatters after file writes.
