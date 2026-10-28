# Sistema local de acceso biométrico

La interfaz y la API se ejecutan únicamente en el equipo local. Node.js sirve la
interfaz y, si se configura, conecta el puerto serial del AS608. FastAPI expone
la API REST y guarda los datos en `database/acceso_local.db` (SQLite). Al iniciar,
FastAPI crea la carpeta, las tablas y la base si aún no existen. Los medicamentos
de `medicamentos tabla.csv` se importan si la tabla está vacía; los cambios
posteriores se conservan en SQLite.

## Requisitos

- Node.js 20 o posterior y npm.
- Python 3.9 o posterior.
- Para el lector físico: Arduino IDE, la biblioteca Adafruit Fingerprint Sensor
  Library y el puerto COM asignado a la placa.

## Instalación e inicio en Windows

Desde PowerShell, en esta carpeta:

```powershell
npm install
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHON = (Resolve-Path .\.venv\Scripts\python.exe).Path
npm start
```

Node espera a que FastAPI haya inicializado y confirmado la base de datos antes
de abrir el puerto de la interfaz. Abre <http://127.0.0.1:3000>. La documentación
interactiva de FastAPI está en <http://127.0.0.1:8000/docs>.

Si se usa un puerto COM diferente, defínelo antes de iniciar Node:

```powershell
$env:FINGERPRINT_PORT = "COM3"
npm start
```

Sin `FINGERPRINT_PORT`, la interfaz y la API funcionan normalmente y el puente
serial queda desactivado. `PORT` y `API_PORT` permiten cambiar los puertos web y
API. `MEDICATIONS_CSV` y `DATABASE_PATH` permiten cambiar las rutas de los datos.
El puerto web y el API se enlazan a `127.0.0.1`, no a la red externa.

## Lector AS608

1. Conecta el sensor al Arduino y carga `Arduino AS608.cpp` desde Arduino IDE,
   instalando la biblioteca Adafruit indicada arriba.
2. El sketch usa el puerto serie USB a 9600 baudios y emite una línea como
   `HuellaID:7` cuando el sensor encuentra una huella que ya está registrada en
   el propio sensor.
3. Anota el ID que el sensor asigna a cada huella. En `/docs`, registra a la
   persona con `POST /api/employees`, proporcionando su ID, nombre,
   `fingerprint_id` y el permiso inicial. Los permisos también se pueden cambiar
   con `PUT /api/employees/{id}/permission`.
4. Cierra el monitor serie del IDE antes de iniciar el servidor; el puerto COM
   solo puede tener un programa conectado a la vez.

Este sketch reconoce huellas ya enroladas, pero no administra el enrolamiento
del sensor. El alta de plantillas se realiza primero desde una rutina de
enrolamiento compatible con el módulo. Si el puerto o los baudios de la placa
son distintos, ajusta `FINGERPRINT_PORT` o el sketch.

## API REST

- `GET /api/health`
- `GET /api/medications?search=para`
- `POST /api/medications`, `PUT /api/medications/{id}`,
  `DELETE /api/medications/{id}`
- `GET /api/employees`, `GET /api/employees/{id}`
- `POST /api/employees`, `PUT /api/employees/{id}`,
  `DELETE /api/employees/{id}`
- `PUT /api/employees/{id}/permission` con `{"authorized": true|false}`
- `POST /api/access/verify` con `{"employee_id":"EMP001"}` o
  `{"fingerprint_id":7}`
- `GET /api/accesses?limit=20`

Las verificaciones por ID y huella consultan el permiso guardado en SQLite y
registran tanto los intentos autorizados como los denegados. Un empleado nuevo
queda denegado por defecto; para asociar una huella, su ID debe ser único y
coincidir con el ID del sensor.

## Base de datos y pruebas locales

SQLite no se ejecuta como un servicio separado: FastAPI crea/abre el archivo
`database/acceso_local.db` al iniciar. Por eso no hace falta abrir un programa
de base de datos aparte. Si ya existe el archivo antiguo `acceso_local.db` en la
carpeta del proyecto, el arranque copia sus datos a la nueva ubicación antes de
inicializar el esquema. La variable `DATABASE_PATH` permite elegir otra ruta.

Para ejecutar las pruebas unitarias de creación, importación y persistencia:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Alcance de seguridad

Es una base de desarrollo local: no incluye autenticación administrativa,
cifrado de la base ni protección para despliegue en red. Mantén los puertos
en `127.0.0.1` y no lo uses como único control de acceso físico a medicamentos
controlados sin añadir controles operativos, autenticación y pruebas del
hardware adecuados.
