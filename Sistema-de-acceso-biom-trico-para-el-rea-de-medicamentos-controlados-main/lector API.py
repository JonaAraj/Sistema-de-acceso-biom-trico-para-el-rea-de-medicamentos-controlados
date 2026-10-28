import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

from database.database import database_connection, initialize_database

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    initialize_database()
    yield


app = FastAPI(
    title="Sistema local de acceso biométrico",
    description="API local para medicamentos, empleados, permisos y accesos.",
    version="1.0.0",
    lifespan=lifespan,
)

class MedicationInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    manufacturer: str = Field(default="", max_length=160)
    dose: str = Field(default="", max_length=80)
    pharmaceutical_form: str = Field(default="", max_length=100)
    lot_number: str = Field(default="", max_length=100)
    price: float = Field(ge=0)
    stock: int = Field(ge=0)


class EmployeeInput(BaseModel):
    id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=160)
    fingerprint_id: Optional[int] = Field(default=None, gt=0)
    authorized: bool = False


class PermissionInput(BaseModel):
    authorized: bool


class AccessAttempt(BaseModel):
    employee_id: Optional[str] = Field(default=None, max_length=50)
    fingerprint_id: Optional[int] = Field(default=None, gt=0)


def employee_record(connection: sqlite3.Connection, employee_id: str):
    return connection.execute(
        """
        SELECT e.id, e.name, e.fingerprint_id,
               COALESCE(p.authorized, 0) AS authorized
        FROM employees AS e
        LEFT JOIN permissions AS p ON p.employee_id = e.id
        WHERE e.id = ?
        """,
        (employee_id,),
    ).fetchone()


def normalized_employee_id(employee_id: str) -> str:
    return employee_id.strip().upper()


def update_permission(
    connection: sqlite3.Connection, employee_id: str, authorized: bool
) -> None:
    connection.execute(
        """
        INSERT INTO permissions (employee_id, authorized, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(employee_id) DO UPDATE SET
            authorized = excluded.authorized,
            updated_at = excluded.updated_at
        """,
        (
            employee_id,
            int(authorized),
            datetime.now(timezone.utc).isoformat(),
        ),
    )


@app.get("/api/health")
def health():
    with database_connection() as connection:
        connection.execute("SELECT 1")
    return {"status": "ok"}


@app.get("/api/medications")
def list_medications(search: Optional[str] = Query(default=None, max_length=160)):
    with database_connection() as connection:
        if search:
            return [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT * FROM medications
                    WHERE name LIKE ? COLLATE NOCASE
                    ORDER BY name
                    """,
                    (f"%{search.strip()}%",),
                )
            ]
        return [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM medications ORDER BY name"
            )
        ]


@app.post("/api/medications", status_code=status.HTTP_201_CREATED)
def create_medication(medication: MedicationInput):
    if not medication.name.strip():
        raise HTTPException(status_code=422, detail="El nombre del medicamento es obligatorio.")
    try:
        with database_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO medications (
                    name, manufacturer, dose, pharmaceutical_form,
                    lot_number, price, stock
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    medication.name.strip(),
                    medication.manufacturer.strip(),
                    medication.dose.strip(),
                    medication.pharmaceutical_form.strip(),
                    medication.lot_number.strip(),
                    medication.price,
                    medication.stock,
                ),
            )
            created = connection.execute(
                "SELECT * FROM medications WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return dict(created)
    except sqlite3.IntegrityError as error:
        raise HTTPException(status_code=409, detail="No se pudo crear el medicamento.") from error


@app.put("/api/medications/{medication_id}")
def replace_medication(medication_id: int, medication: MedicationInput):
    if not medication.name.strip():
        raise HTTPException(status_code=422, detail="El nombre del medicamento es obligatorio.")
    with database_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE medications SET
                name = ?, manufacturer = ?, dose = ?, pharmaceutical_form = ?,
                lot_number = ?, price = ?, stock = ?
            WHERE id = ?
            """,
            (
                medication.name.strip(),
                medication.manufacturer.strip(),
                medication.dose.strip(),
                medication.pharmaceutical_form.strip(),
                medication.lot_number.strip(),
                medication.price,
                medication.stock,
                medication_id,
            ),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Medicamento no encontrado.")
        return dict(
            connection.execute(
                "SELECT * FROM medications WHERE id = ?", (medication_id,)
            ).fetchone()
        )


@app.delete("/api/medications/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_medication(medication_id: int):
    with database_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM medications WHERE id = ?", (medication_id,)
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Medicamento no encontrado.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/employees")
def list_employees():
    with database_connection() as connection:
        return [
            {**dict(row), "authorized": bool(row["authorized"])}
            for row in connection.execute(
                """
                SELECT e.id, e.name, e.fingerprint_id,
                       COALESCE(p.authorized, 0) AS authorized,
                       p.updated_at AS permission_updated_at
                FROM employees AS e
                LEFT JOIN permissions AS p ON p.employee_id = e.id
                ORDER BY e.name
                """
            )
        ]


@app.post("/api/employees", status_code=status.HTTP_201_CREATED)
def create_employee(employee: EmployeeInput):
    normalized_id = normalized_employee_id(employee.id)
    if not normalized_id or not employee.name.strip():
        raise HTTPException(
            status_code=422, detail="El ID y nombre del empleado son obligatorios."
        )

    try:
        with database_connection() as connection:
            connection.execute(
                "INSERT INTO employees (id, name, fingerprint_id) VALUES (?, ?, ?)",
                (normalized_id, employee.name.strip(), employee.fingerprint_id),
            )
            update_permission(connection, normalized_id, employee.authorized)
            created = employee_record(connection, normalized_id)
            return {**dict(created), "authorized": bool(created["authorized"])}
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail="El ID o la huella ya están registrados.",
        ) from error


@app.get("/api/employees/{employee_id}")
def get_employee(employee_id: str):
    with database_connection() as connection:
        employee = employee_record(connection, normalized_employee_id(employee_id))
        if employee is None:
            raise HTTPException(status_code=404, detail="Empleado no encontrado.")
        return {**dict(employee), "authorized": bool(employee["authorized"])}


@app.put("/api/employees/{employee_id}")
def replace_employee(employee_id: str, employee: EmployeeInput):
    normalized_id = normalized_employee_id(employee_id)
    if normalized_employee_id(employee.id) != normalized_id:
        raise HTTPException(status_code=422, detail="El ID del cuerpo no coincide con la URL.")
    if not employee.name.strip():
        raise HTTPException(status_code=422, detail="El nombre del empleado es obligatorio.")

    try:
        with database_connection() as connection:
            cursor = connection.execute(
                "UPDATE employees SET name = ?, fingerprint_id = ? WHERE id = ?",
                (employee.name.strip(), employee.fingerprint_id, normalized_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Empleado no encontrado.")
            update_permission(connection, normalized_id, employee.authorized)
            updated = employee_record(connection, normalized_id)
            return {**dict(updated), "authorized": bool(updated["authorized"])}
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=409, detail="La huella ya está asignada a otro empleado."
        ) from error


@app.put("/api/employees/{employee_id}/permission")
def set_employee_permission(employee_id: str, permission: PermissionInput):
    normalized_id = normalized_employee_id(employee_id)
    with database_connection() as connection:
        if employee_record(connection, normalized_id) is None:
            raise HTTPException(status_code=404, detail="Empleado no encontrado.")
        update_permission(connection, normalized_id, permission.authorized)
        employee = employee_record(connection, normalized_id)
        return {**dict(employee), "authorized": bool(employee["authorized"])}


@app.delete("/api/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(employee_id: str):
    with database_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM employees WHERE id = ?",
            (normalized_employee_id(employee_id),),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Empleado no encontrado.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/access/verify")
def verify_access(attempt: AccessAttempt):
    has_employee_id = attempt.employee_id is not None
    has_fingerprint_id = attempt.fingerprint_id is not None
    if has_employee_id == has_fingerprint_id:
        raise HTTPException(
            status_code=422,
            detail="Envíe exactamente uno: employee_id o fingerprint_id.",
        )

    if has_employee_id:
        credential = normalized_employee_id(attempt.employee_id)
        if not credential:
            raise HTTPException(status_code=422, detail="El ID de empleado es obligatorio.")
        method = "employee_id"
        lookup = "e.id = ?"
        lookup_value = credential
    else:
        credential = str(attempt.fingerprint_id)
        method = "fingerprint"
        lookup = "e.fingerprint_id = ?"
        lookup_value = attempt.fingerprint_id

    with database_connection() as connection:
        employee = connection.execute(
            f"""
            SELECT e.id, e.name, e.fingerprint_id,
                   COALESCE(p.authorized, 0) AS authorized
            FROM employees AS e
            LEFT JOIN permissions AS p ON p.employee_id = e.id
            WHERE {lookup}
            """,
            (lookup_value,),
        ).fetchone()
        authorized = employee is not None and bool(employee["authorized"])
        reason = (
            "authorized"
            if authorized
            else "permission_denied"
            if employee is not None
            else "credential_not_registered"
        )
        cursor = connection.execute(
            """
            INSERT INTO accesses (
                employee_id, credential, method, authorized, reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                employee["id"] if employee is not None else None,
                credential,
                method,
                int(authorized),
                reason,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        return {
            "access_id": cursor.lastrowid,
            "authorized": authorized,
            "reason": reason,
            "employee": (
                {
                    "id": employee["id"],
                    "name": employee["name"],
                    "fingerprint_id": employee["fingerprint_id"],
                }
                if employee is not None
                else None
            ),
        }


@app.get("/api/accesses")
def list_accesses(limit: int = Query(default=20, ge=1, le=100)):
    with database_connection() as connection:
        return [
            {**dict(row), "authorized": bool(row["authorized"])}
            for row in connection.execute(
                """
                SELECT a.id, a.employee_id, e.name AS employee_name,
                       a.credential, a.method, a.authorized, a.reason, a.created_at
                FROM accesses AS a
                LEFT JOIN employees AS e ON e.id = a.employee_id
                ORDER BY a.id DESC
                LIMIT ?
                """,
                (limit,),
            )
        ]


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=int(os.getenv("API_PORT", "8000")),
        log_level="info",
    )