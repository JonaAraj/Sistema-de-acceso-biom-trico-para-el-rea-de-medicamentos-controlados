import csv
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator


PROJECT_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE_PATH = DATABASE_DIR / "acceso_local.db"
DATABASE_PATH = Path(
    os.getenv("DATABASE_PATH", str(DEFAULT_DATABASE_PATH))
).resolve()
MEDICATIONS_CSV = Path(
    os.getenv("MEDICATIONS_CSV", str(PROJECT_DIR / "medicamentos tabla.csv"))
).resolve()
LEGACY_DATABASE_PATH = PROJECT_DIR / "acceso_local.db"


@contextmanager
def database_connection() -> Generator[sqlite3.Connection, None, None]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def migrate_legacy_database() -> None:
    if (
        DATABASE_PATH == DEFAULT_DATABASE_PATH.resolve()
        and not DATABASE_PATH.exists()
        and LEGACY_DATABASE_PATH.is_file()
    ):
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(LEGACY_DATABASE_PATH)
        destination = sqlite3.connect(DATABASE_PATH)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()
        print(f"Base SQLite anterior migrada a: {DATABASE_PATH}")


def import_medications(connection: sqlite3.Connection) -> None:
    if not MEDICATIONS_CSV.is_file():
        raise FileNotFoundError(f"No se encontró el archivo CSV: {MEDICATIONS_CSV}")

    with MEDICATIONS_CSV.open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required_columns = {
            "id",
            "nombre",
            "fabricante",
            "dosis",
            "forma_farmacologica",
            "numero_lote",
            "precio",
            "existencia",
        }
        missing_columns = required_columns.difference(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(
                f"Faltan columnas en {MEDICATIONS_CSV}: "
                f"{', '.join(sorted(missing_columns))}"
            )

        for line_number, medication in enumerate(reader, start=2):
            try:
                name = (medication["nombre"] or "").strip()
                if not name:
                    raise ValueError("el nombre del medicamento está vacío")
                connection.execute(
                    """
                    INSERT OR IGNORE INTO medications (
                        id, name, manufacturer, dose, pharmaceutical_form,
                        lot_number, price, stock
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        int(medication["id"]),
                        name,
                        (medication["fabricante"] or "").strip(),
                        (medication["dosis"] or "").strip(),
                        (medication["forma_farmacologica"] or "").strip(),
                        (medication["numero_lote"] or "").strip(),
                        float(medication["precio"]),
                        int(medication["existencia"]),
                    ),
                )
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(
                    f"Fila {line_number} inválida en {MEDICATIONS_CSV}: {error}"
                ) from error


def initialize_database() -> None:
    migrate_legacy_database()
    with database_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS medications (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                manufacturer TEXT NOT NULL DEFAULT '',
                dose TEXT NOT NULL DEFAULT '',
                pharmaceutical_form TEXT NOT NULL DEFAULT '',
                lot_number TEXT NOT NULL DEFAULT '',
                price REAL NOT NULL DEFAULT 0 CHECK (price >= 0),
                stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0)
            );

            CREATE TABLE IF NOT EXISTS employees (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                fingerprint_id INTEGER UNIQUE CHECK (
                    fingerprint_id IS NULL OR fingerprint_id > 0
                )
            );

            CREATE TABLE IF NOT EXISTS permissions (
                employee_id TEXT PRIMARY KEY
                    REFERENCES employees(id) ON DELETE CASCADE,
                authorized INTEGER NOT NULL DEFAULT 0
                    CHECK (authorized IN (0, 1)),
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS accesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT
                    REFERENCES employees(id) ON DELETE SET NULL,
                credential TEXT NOT NULL,
                method TEXT NOT NULL CHECK (method IN ('employee_id', 'fingerprint')),
                authorized INTEGER NOT NULL CHECK (authorized IN (0, 1)),
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        medication_count = connection.execute(
            "SELECT COUNT(*) FROM medications"
        ).fetchone()[0]
        if medication_count == 0:
            import_medications(connection)
