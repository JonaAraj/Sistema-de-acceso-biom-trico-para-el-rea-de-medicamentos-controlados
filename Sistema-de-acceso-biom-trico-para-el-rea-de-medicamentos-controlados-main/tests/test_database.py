import sqlite3
import tempfile
import unittest
from pathlib import Path

from database import database as database_module


class DatabaseInitializationTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp_directory.name)
        self.previous_values = {
            name: getattr(database_module, name)
            for name in (
                "DATABASE_PATH",
                "DEFAULT_DATABASE_PATH",
                "MEDICATIONS_CSV",
                "LEGACY_DATABASE_PATH",
            )
        }
        self.database_path = self.directory / "database" / "acceso_local.db"
        self.csv_path = self.directory / "medicamentos.csv"
        self.csv_path.write_text(
            "id,nombre,fabricante,dosis,forma_farmacologica,numero_lote,precio,existencia\n"
            "1,Paracetamol,Bayer,500,Tableta,BAY1,50,200\n"
            "2,Ibuprofeno,Advil,400,Tableta,ADV2,70,150\n",
            encoding="utf-8",
        )
        database_module.DATABASE_PATH = self.database_path
        database_module.DEFAULT_DATABASE_PATH = self.database_path
        database_module.MEDICATIONS_CSV = self.csv_path
        database_module.LEGACY_DATABASE_PATH = self.directory / "legacy.db"

    def tearDown(self):
        for name, value in self.previous_values.items():
            setattr(database_module, name, value)
        self.temp_directory.cleanup()

    def test_creates_schema_and_imports_csv_once(self):
        self.assertFalse(self.database_path.exists())

        database_module.initialize_database()

        self.assertTrue(self.database_path.is_file())
        with database_module.database_connection() as connection:
            tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertTrue(
                {"medications", "employees", "permissions", "accesses"}.issubset(
                    tables
                )
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM medications").fetchone()[0],
                2,
            )
            connection.execute(
                "UPDATE medications SET stock = 17 WHERE id = 1"
            )

        database_module.initialize_database()

        with database_module.database_connection() as connection:
            self.assertEqual(
                connection.execute(
                    "SELECT stock FROM medications WHERE id = 1"
                ).fetchone()[0],
                17,
            )
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM medications").fetchone()[0],
                2,
            )

    def test_migrates_existing_database_before_schema_setup(self):
        legacy_path = self.directory / "legacy.db"
        connection = sqlite3.connect(legacy_path)
        try:
            connection.execute(
                """
                CREATE TABLE medications (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    manufacturer TEXT NOT NULL DEFAULT '',
                    dose TEXT NOT NULL DEFAULT '',
                    pharmaceutical_form TEXT NOT NULL DEFAULT '',
                    lot_number TEXT NOT NULL DEFAULT '',
                    price REAL NOT NULL DEFAULT 0,
                    stock INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            connection.execute(
                "INSERT INTO medications (id, name, stock) VALUES (9, 'Existente', 31)"
            )
            connection.commit()
        finally:
            connection.close()
        database_module.LEGACY_DATABASE_PATH = legacy_path

        database_module.initialize_database()

        with database_module.database_connection() as connection:
            medication = connection.execute(
                "SELECT name, stock FROM medications WHERE id = 9"
            ).fetchone()
            self.assertEqual((medication["name"], medication["stock"]), ("Existente", 31))
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM medications").fetchone()[0],
                1,
            )


if __name__ == "__main__":
    unittest.main()
