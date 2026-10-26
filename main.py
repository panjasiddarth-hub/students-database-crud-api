"""FastAPI + SQLite student records CRUD application."""

from contextlib import asynccontextmanager
from datetime import date
import os
from pathlib import Path
import sqlite3
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


DATABASE_PATH = Path(os.getenv("STUDENT_DATABASE_PATH", Path(__file__).with_name("students.db")))


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                student_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date_of_birth TEXT NOT NULL,
                email TEXT COLLATE NOCASE UNIQUE,
                phone TEXT,
                course TEXT,
                address TEXT,
                enrollment_date TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Students Database API",
    description="A simple student records API backed by SQLite.",
    version="1.0.0",
    lifespan=lifespan,
)


class StudentFields(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120, examples=["Aarav Sharma"])
    date_of_birth: date = Field(examples=["2005-04-18"])
    email: str | None = Field(default=None, max_length=254, examples=["aarav@example.com"])
    phone: str | None = Field(default=None, max_length=30, examples=["+91 98765 43210"])
    course: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=300)
    enrollment_date: date | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None):
        if value is not None and ("@" not in value or value.startswith("@") or value.endswith("@") or "." not in value.rsplit("@", 1)[-1] or any(ch.isspace() for ch in value)):
            raise ValueError("Enter a valid email address.")
        return value

    @model_validator(mode="after")
    def require_contact(self):
        if not self.email and not self.phone:
            raise ValueError("Provide at least one contact field: email or phone.")
        return self


class StudentCreate(StudentFields):
    pass


class StudentUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    date_of_birth: date | None = None
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=30)
    course: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=300)
    enrollment_date: date | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None):
        if value is not None and ("@" not in value or value.startswith("@") or value.endswith("@") or "." not in value.rsplit("@", 1)[-1] or any(ch.isspace() for ch in value)):
            raise ValueError("Enter a valid email address.")
        return value

    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")
        for required in ("name", "date_of_birth"):
            if required in self.model_fields_set and getattr(self, required) is None:
                raise ValueError(f"{required} cannot be null.")
        return self


class Student(StudentFields):
    student_id: int
    created_at: str

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


def row_to_student(row: sqlite3.Row) -> Student:
    values = dict(row)
    values["date_of_birth"] = date.fromisoformat(values["date_of_birth"])
    if values["enrollment_date"]:
        values["enrollment_date"] = date.fromisoformat(values["enrollment_date"])
    return Student.model_validate(values)


def fetch_student(student_id: int) -> Student:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM students WHERE student_id = ?", (student_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Student not found.")
    return row_to_student(row)


@app.get("/", tags=["Health"])
def root():
    return {"message": "Students Database API", "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}


@app.post("/students", response_model=Student, status_code=status.HTTP_201_CREATED, tags=["Students"])
def create_student(student: StudentCreate):
    values = student.model_dump(mode="json")
    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """INSERT INTO students
                (name, date_of_birth, email, phone, course, address, enrollment_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    values["name"], values["date_of_birth"], values["email"],
                    values["phone"], values["course"], values["address"],
                    values["enrollment_date"],
                ),
            )
            student_id = cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="A student with this email already exists.") from exc
    return fetch_student(student_id)


@app.get("/students", response_model=list[Student], tags=["Students"])
def list_students(
    name: Annotated[str | None, Query(max_length=120, description="Case-insensitive partial match")] = None,
    email: Annotated[str | None, Query(max_length=254)] = None,
    course: Annotated[str | None, Query(max_length=120)] = None,
    born_after: date | None = None,
    born_before: date | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    clauses: list[str] = []
    parameters: list[object] = []
    if name:
        clauses.append("name LIKE ? COLLATE NOCASE")
        parameters.append(f"%{name}%")
    if email:
        clauses.append("email = ? COLLATE NOCASE")
        parameters.append(email)
    if course:
        clauses.append("course LIKE ? COLLATE NOCASE")
        parameters.append(f"%{course}%")
    if born_after:
        clauses.append("date_of_birth > ?")
        parameters.append(born_after.isoformat())
    if born_before:
        clauses.append("date_of_birth < ?")
        parameters.append(born_before.isoformat())
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_connection() as connection:
        rows = connection.execute(
            f"SELECT * FROM students {where} ORDER BY student_id LIMIT ? OFFSET ?",
            (*parameters, limit, offset),
        ).fetchall()
    return [row_to_student(row) for row in rows]


@app.get("/students/{student_id}", response_model=Student, tags=["Students"])
def get_student(student_id: int):
    return fetch_student(student_id)


@app.put("/students/{student_id}", response_model=Student, tags=["Students"])
def update_student(student_id: int, updates: StudentUpdate):
    current = fetch_student(student_id)
    data = current.model_dump(mode="json")
    data.update(updates.model_dump(mode="json", exclude_unset=True))
    if not data.get("email") and not data.get("phone"):
        raise HTTPException(status_code=422, detail="A student must have an email address or phone number.")
    fields = updates.model_fields_set
    if not fields:
        raise HTTPException(status_code=422, detail="Provide at least one field to update.")
    assignments = ", ".join(f"{field} = ?" for field in fields)
    values = [data[field] for field in fields]
    try:
        with get_connection() as connection:
            connection.execute(
                f"UPDATE students SET {assignments} WHERE student_id = ?",
                (*values, student_id),
            )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="A student with this email already exists.") from exc
    return fetch_student(student_id)


@app.patch("/students/{student_id}", response_model=Student, tags=["Students"])
def patch_student(student_id: int, updates: StudentUpdate):
    return update_student(student_id, updates)


@app.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Students"])
def delete_student(student_id: int):
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Student not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
