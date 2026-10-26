# Students Database CRUD API

A beginner-friendly student records backend built with **Python**, **FastAPI**, and **SQLite**. It supports creating, listing, filtering, viewing, updating, and deleting records. The optional Ollama extension from the assignment is not included.

## Requirements

- Python 3.10 or newer
- `pip`

## Install and run

From this folder, create and activate a virtual environment, then install the dependencies:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

Start the development server:

```bash
uvicorn main:app --reload
```

The database file `students.db` is created beside `main.py` the first time the app starts. To use another location, set `STUDENT_DATABASE_PATH` before starting the app.

## API documentation

- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- Health check: <http://127.0.0.1:8000/health>

## Student fields

`name` and `date_of_birth` are required. At least one of `email` and `phone` must be provided. `course`, `address`, and `enrollment_date` are optional. Dates use `YYYY-MM-DD`. Email addresses must be unique when supplied.

## Example requests

Create a student:

```bash
curl -X POST http://127.0.0.1:8000/students \
  -H "Content-Type: application/json" \
  -d '{"name":"Aarav Sharma","date_of_birth":"2005-04-18","email":"aarav@example.com","phone":"+91 98765 43210","course":"Python Backend","enrollment_date":"2026-10-01"}'
```

List students, optionally filtering by partial name/course, exact email, or date of birth:

```bash
curl "http://127.0.0.1:8000/students?name=aarav&course=python&born_after=2000-01-01&limit=20"
```

Get one student:

```bash
curl http://127.0.0.1:8000/students/1
```

Update one or more fields (both `PUT` and `PATCH` accept partial updates):

```bash
curl -X PATCH http://127.0.0.1:8000/students/1 \
  -H "Content-Type: application/json" \
  -d '{"course":"Advanced Python Backend"}'
```

Delete a student (successful response is `204 No Content`):

```bash
curl -X DELETE http://127.0.0.1:8000/students/1
```

## Response and errors

Student IDs are generated automatically. A missing record returns `404`, a duplicate email returns `409`, and invalid input returns `422` with details. List results are ordered by ID and support `limit` (1-100) and `offset` pagination.

## Project layout

```text
.
├── main.py            # API routes, validation, and SQLite persistence
├── requirements.txt   # Python dependencies
├── .gitignore         # Excludes local database and environment files
└── README.md          # Setup and API usage
```

## GitHub submission

Initialize a Git repository, commit the source files, and push it to a GitHub repository. Do not add real student personal information, passwords, or secrets. The local SQLite database is ignored by Git.
