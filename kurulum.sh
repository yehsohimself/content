#!/bin/bash
# Content install (macOS, Apple silicon). No sudo. Needs Homebrew (https://brew.sh) and Git.
# Kurulum (macOS, Apple işlemci). Sudo istemez; Homebrew ve Git gerekir.
set -e
cd "$(dirname "$0")"

echo "1/3 Tools via Homebrew: ffmpeg, deno (yt-dlp needs it for YouTube), uv"
if ! command -v brew >/dev/null; then echo "Homebrew not found. Install it first: https://brew.sh"; exit 1; fi
for p in ffmpeg deno uv; do brew list "$p" >/dev/null 2>&1 || brew install "$p"; done

echo "2/3 Python environment (.venv) and packages"
[ -d .venv ] || uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt
if [ "$1" = "--shazam" ]; then uv pip install --python .venv/bin/python "shazamio>=0.9"; fi
mkdir -p content kayitlar

echo "3/3 Claude"
if command -v claude >/dev/null || ls "$HOME/.local/bin/claude" >/dev/null 2>&1 || ls "$HOME/Library/Application Support/Claude/claude-code" >/dev/null 2>&1; then
  echo "   Claude Code found. If you have not signed in yet: claude auth login"
else
  echo "   Claude Code not found. Content needs it to look at the video and write the guide:"
  echo "   https://claude.com/claude-code  (then: claude auth login)"
fi

echo
echo "Done. Start with:"
echo "    .venv/bin/python content_sunucu.py"
echo "then open http://127.0.0.1:8769 (later: double-click Content.command)."
echo "Optional song recognition: ./kurulum.sh --shazam, then turn it on in Settings."
