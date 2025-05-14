from database import SessionLocal
from models import Empleado

db = SessionLocal()
empleados = [
    Empleado(id=12345, nombre="Juan Pérez"),
    Empleado(id=67890, nombre="Ana Gómez")
]
db.add_all(empleados)
db.commit()
db.close()
