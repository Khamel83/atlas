**When generating shell code:**

- Use portable POSIX `sh` only; no bash/zsh/fishisms.
- Shebang: `#!/usr/bin/env sh`.
- Assume macOS has GNU coreutils via Homebrew (coreutils, findutils, gnu-sed, grep) with gnubin in PATH; Ubuntu has standard GNU.
- For `sed -i` and `date`, either rely on `scripts/posix/portable.sh` or implement portable flags.
- Use `getopts`, `printf`, `mktemp`, `trap`, `find -print0 | xargs -0`.
- Must pass `shellcheck -s sh` and be `shfmt -ln posix` clean.