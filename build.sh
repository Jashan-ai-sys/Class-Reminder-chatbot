#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
export PLAYWRIGHT_BROWSERS_PATH=/opt/render/project/src/pw-browsers
playwright install chromium
