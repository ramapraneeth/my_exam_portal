#!/usr/bin/env bash
# Render runs this automatically on every deploy as the Build Command.
# This is what creates/updates your tables in Supabase Postgres -
# you never need shell access or to run `migrate` by hand on Render.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
