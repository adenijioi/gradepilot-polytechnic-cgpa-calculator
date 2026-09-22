# GradePilot — Polytechnic CGPA Calculator

A responsive Flask/PostgreSQL application for calculating GPA and CGPA across four semesters, with up to 15 courses per semester.

## Local setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --debug
```
Without `DATABASE_URL`, SQLite is used locally. The included `render.yaml` provisions the web service and PostgreSQL database on Render.
