#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
export PLAYWRIGHT_BROWSERS_PATH=$HOME/pw-browsers
playwright install chromium
