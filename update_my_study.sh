#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
python3 tools/generate_personal_dashboard.py
git add "我的考研系统"
git commit -m "Update my study log" || true
git -c http.version=HTTP/1.1 push origin main

