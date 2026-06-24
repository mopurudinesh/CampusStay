#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Compile static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate

# Seed database with default users, blocks, and rooms
python manage.py seed_db

