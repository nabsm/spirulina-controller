#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "==> Pulling latest code..."
git pull

echo "==> Installing Python dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt

echo "==> Building frontend..."
cd dashboard
npm install --silent
npm run build
cd ..

echo "==> Restarting backend..."
sudo systemctl restart spirulina

echo "==> Done! Check status with: sudo systemctl status spirulina"
