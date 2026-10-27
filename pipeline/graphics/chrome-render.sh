#!/bin/sh
# Written by AI on 2026-10-16 by GPT-6 Codex. Edited 2026-10-18 by Claude Opus 5.5: run Remotion's own downloaded
# headless shell, not the installed Google Chrome app; every launch of the app left a ~1.5 GB code-sign clone in
# /private/var/folders/.../X/com.google.Chrome.code_sign_clone (236 of them by 18 Oct).
# Use software rasterization for deterministic offline frames.
here=$(cd "$(dirname "$0")" && pwd)
exec "$here/node_modules/.remotion/chrome-headless-shell/mac-arm64/chrome-headless-shell-mac-arm64/chrome-headless-shell" --disable-gpu --disable-gpu-rasterization "$@"
