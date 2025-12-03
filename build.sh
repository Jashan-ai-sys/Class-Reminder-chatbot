#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
# playwright install-deps chromium  <-- Removed because it requires root/sudo which Render doesn't allow in build
