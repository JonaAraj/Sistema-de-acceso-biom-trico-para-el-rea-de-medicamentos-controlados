const express = require("express");
const http = require("http");
const path = require("path");
const { spawn } = require("child_process");
const { SerialPort } = require("serialport");
const { ReadlineParser } = require("@serialport/parser-readline");

const HOST = "127.0.0.1";
const WEB_PORT = Number(process.env.PORT || 3000);
const API_PORT = Number(process.env.API_PORT || 8000);
const API_URL = `http://${HOST}:${API_PORT}`;
const DATABASE_PATH = path.resolve(
  process.env.DATABASE_PATH ||
    path.join(__dirname, "database", "acceso_local.db"),
);
const PYTHON = process.env.PYTHON || "python";
const SERIAL_PORT_PATH = process.env.FINGERPRINT_PORT;
const BAUD_RATE = 9600;

const app = express();
const server = http.createServer(app);
let shuttingDown = false;
let apiProcessExited = false;
let apiProcessError = null;

const apiProcess = spawn(PYTHON, [path.join(__dirname, "lector API.py")], {
  cwd: __dirname,
  env: {
    ...process.env,
    API_PORT: String(API_PORT),
    DATABASE_PATH,
    PYTHONUNBUFFERED: "1",
  },
  stdio: "inherit",
});

apiProcess.on("error", (error) => {
  apiProcessError = error;
  console.error(`No se pudo iniciar FastAPI con "${PYTHON}":`, error.message);
  process.exitCode = 1;
  if (server.listening) server.close();
});

apiProcess.on("exit", (code, signal) => {
  apiProcessExited = true;
  if (!shuttingDown) {
    console.error(
      `FastAPI terminó inesperadamente (código ${code}, señal ${signal || "ninguna"}).`,
    );
    process.exitCode = code || 1;
    if (server.listening) server.close();
  }
});

const publicFiles = new Map([
  ["/", "Index AB.html"],
  ["/Index AB.html", "Index AB.html"],
  ["/style.css", "style.css"],
  ["/api-client.js", "api-client.js"],
  ["/main.js", "main.js"],
  ["/emp-verificacion.js", "Emp verificacion.js"],
  ["/panel-acceso.js", "panel de acceso.js"],
]);

for (const [route, filename] of publicFiles) {
  app.get(route, (_request, response) => {
    response.sendFile(path.join(__dirname, filename));
  });
}

app.use(
  "/imagenes",
  express.static(path.join(__dirname, "imagenes"), { dotfiles: "deny" }),
);

app.use("/api", (request, response) => {
  const proxyRequest = http.request(
    {
      hostname: HOST,
      port: API_PORT,
      path: request.originalUrl,
      method: request.method,
      headers: {
        ...request.headers,
        host: `${HOST}:${API_PORT}`,
      },
    },
    (proxyResponse) => {
      response.writeHead(proxyResponse.statusCode || 502, proxyResponse.headers);
      proxyResponse.pipe(response);
    },
  );

  proxyRequest.on("error", (error) => {
    console.error("No se pudo contactar la API local:", error.message);
    if (!response.headersSent) {
      response.status(502).json({ detail: "La API local no está disponible." });
    }
  });

  request.pipe(proxyRequest);
});

app.use((_request, response) => {
  response.status(404).send("Recurso no encontrado.");
});

function connectFingerprintReader() {
  if (!SERIAL_PORT_PATH) {
    console.log(
      "Lector AS608 desactivado. Configure FINGERPRINT_PORT (por ejemplo, COM3).",
    );
    return;
  }

  const port = new SerialPort({
    path: SERIAL_PORT_PATH,
    baudRate: BAUD_RATE,
    autoOpen: false,
  });
  const parser = port.pipe(new ReadlineParser({ delimiter: "\n" }));

  port.on("error", (error) => {
    console.error(`Error del lector en ${SERIAL_PORT_PATH}:`, error.message);
  });
  port.open((error) => {
    if (error) {
      console.error(`No se pudo abrir ${SERIAL_PORT_PATH}:`, error.message);
      return;
    }
    console.log(`Lector AS608 conectado en ${SERIAL_PORT_PATH} a ${BAUD_RATE} baudios.`);
  });

  parser.on("data", (line) => {
    const match = line.trim().match(/^HuellaID:(\d+)$/);
    if (match) {
      void reportFingerprint(Number(match[1]));
    }
  });
}

async function reportFingerprint(fingerprintId) {
  try {
    const response = await fetch(`${API_URL}/api/access/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fingerprint_id: fingerprintId }),
    });
    const result = await response.json();
    if (!response.ok) {
      console.error("La API rechazó la lectura del sensor:", result);
      return;
    }

    const employeeName = result.employee ? ` (${result.employee.name})` : "";
    console.log(
      `Huella ${fingerprintId}: ${result.authorized ? "acceso autorizado" : "acceso denegado"}${employeeName}.`,
    );
  } catch (error) {
    console.error("No se pudo enviar la lectura del sensor a FastAPI:", error.message);
  }
}

function shutdown(signal) {
  if (shuttingDown) return;
  shuttingDown = true;
  console.log(`Cerrando servidores (${signal}).`);
  apiProcess.kill();
  if (server.listening) server.close();
}

process.once("SIGINT", () => shutdown("SIGINT"));
process.once("SIGTERM", () => shutdown("SIGTERM"));

async function waitForApi(timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  let lastError;

  while (Date.now() < deadline && !shuttingDown) {
    if (apiProcessError) throw apiProcessError;
    if (apiProcessExited) {
      throw new Error("FastAPI terminó antes de inicializar la base de datos.");
    }

    try {
      const response = await fetch(`${API_URL}/api/health`, {
        signal: AbortSignal.timeout(1000),
      });
      if (response.ok && (await response.json()).status === "ok") return;
      lastError = new Error(`FastAPI respondió HTTP ${response.status}.`);
    } catch (error) {
      lastError = error;
    }

    await new Promise((resolve) => setTimeout(resolve, 500));
  }

  if (!shuttingDown) {
    throw new Error(
      `FastAPI/SQLite no estuvo disponible después de ${timeoutMs / 1000} segundos: ${lastError?.message || "sin respuesta"}`,
    );
  }
}

async function startServer() {
  try {
    await waitForApi();
    if (shuttingDown) return;

    server.listen(WEB_PORT, HOST, () => {
      console.log(`Interfaz local: http://${HOST}:${WEB_PORT}`);
      console.log(`API REST local: http://${HOST}:${API_PORT}/docs`);
      console.log(`Base SQLite local: ${DATABASE_PATH}`);
      connectFingerprintReader();
    });
  } catch (error) {
    if (shuttingDown) return;
    console.error("No se inició la interfaz porque FastAPI/SQLite no está listo:", error.message);
    process.exitCode = 1;
    apiProcess.kill();
  }
}

void startServer();
