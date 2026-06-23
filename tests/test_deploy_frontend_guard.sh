#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

grep -q 'Navigate to="/platform?tab=data-elements"' "$ROOT_DIR/frontend/src/App.jsx"
test -f "$ROOT_DIR/frontend/src/pages/PlatformOverviewPage.jsx"
test -f "$ROOT_DIR/backend/app/api/openks_routes.py"
test -f "$ROOT_DIR/backend/app/api/platform_overview_routes.py"
grep -q 'app.api.openks_routes' "$ROOT_DIR/backend/app/api/__init__.py"
grep -q 'app.api.platform_overview_routes' "$ROOT_DIR/backend/app/api/__init__.py"

echo "frontend/backend platform overview guards passed"
