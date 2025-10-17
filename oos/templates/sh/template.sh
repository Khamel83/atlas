#!/usr/bin/env sh
# shellcheck shell=sh
set -eu
[ -f "$HOME/.config/sh/portable.sh" ] && . "$HOME/.config/sh/portable.sh" || true
[ -f "$(dirname "$0")/../../scripts/posix/portable.sh" ] && . "$(dirname "$0")/../../scripts/posix/portable.sh" || true

usage() { printf 'Usage: %s [-n name]\n' "${0##*/}"; }
name="world"
while getopts ":n:h" opt; do
	case "$opt" in
	n) name="$OPTARG" ;;
	h)
		usage
		exit 0
		;;
	\?)
		usage
		exit 2
		;;
	esac
done

tmp="$(p_mktemp 2>/dev/null || mktemp)"
p_echo "Hello, $name" >"$tmp"
p_echo "Wrote: $(p_realpath "$tmp")"
