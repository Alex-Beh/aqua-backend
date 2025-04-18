#!/bin/bash

# Exit on error
set -e

echo "🔧 Setting up Flask-Migrate for your project..."

# Step 1: Set FLASK_APP to manage.py
export FLASK_APP=manage.py
echo "📌 FLASK_APP set to manage.py"

# Step 2: Initialize migrations (creates migrations/ folder)
if [ ! -d "migrations" ]; then
  echo "📁 Running flask db init..."
  python -m flask db init
else
  echo "✅ Migrations folder already exists. Skipping init."
fi

# Step 3: Generate migration from models
echo "📝 Generating migration..."
python -m flask db migrate -m "Initial migration"

# Step 4: Apply migration to database
echo "🚀 Applying migration (flask db upgrade)..."
python -m flask db upgrade

echo "✅ Database is now up to date with models!"
