# shellcheck shell=sh
# Minimal BSD/Linux portability helpers.
set -eu
umask 022

_have() { command -v "$1" >/dev/null 2>&1; }

# Prefer GNU 'date' on macOS if installed via Homebrew.
p_date() { if _have gdate; then gdate "$@"; else date "$@"; fi; }

# sed -i portability (GNU: -i'', BSD: -i ''); usage: p_sedi 's/a/b/g' file...
p_sedi() {
	if sed --version >/dev/null 2>&1; then
		sed -i'' "$@"
	else
		sed -i '' "$@"
	fi
}

# Realpath that works on macOS without coreutils
p_realpath() {
	# usage: p_realpath path
	if _have realpath; then realpath "$1"; elif _have grealpath; then grealpath "$1"; else
		(cd "$(dirname "$1")" 2>/dev/null && fname=$(basename "$1") &&
			if [ -d "$fname" ]; then cd "$fname" && pwd; else printf '%s/%s\n' "$(pwd)" "$fname"; fi)
	fi
}

p_mktemp() { mktemp "${TMPDIR:-/tmp}/oos.XXXXXX"; }
p_echo() { printf '%s\n' "$*"; }
p_find0() { find "$1" -type f -print0; }
p_xargs0() { xargs -0 "$@"; }
die() {
	printf 'error: %s\n' "$*" >&2
	exit 1
}
