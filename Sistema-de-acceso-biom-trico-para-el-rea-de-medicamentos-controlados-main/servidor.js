const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const SerialPort = require('serialport');
const Readline = require('@serialport/parser-readline');
const sqlite3 = require('sqlite3').verbose();

// === CONFIGURACIÓN ===
const SERIAL_PORT = 'COM3';
const BAUD_RATE = 9600;
const DB_PATH = './bd_huellas.db';

// === INICIAR EXPRESS Y WEBSOCKET ===
const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// === SERVIR FRONTEND ===
app.use(express.static(__dirname));

// === CONECTAR A BASE DE DATOS ===
const db = new sqlite3.Database(DB_PATH, (err) => {
  if (err) return console.error("❌ Error al conectar la BD:", err.message);
  console.log("✅ Base de datos conectada");
});

// === LEER ARDUINO POR SERIAL ===
const port = new SerialPort(SERIAL_PORT, { baudRate: BAUD_RATE });
const parser = port.pipe(new Readline({ delimiter: '\n' }));

parser.on('data', (line) => {
  line = line.trim();
  console.log("🔹 Desde Arduino:", line);

  if (line.startsWith("HuellaID:")) {
    const huellaId = parseInt(line.split(":")[1]);
    verificarHuella(huellaId);
  }
});

// === LÓGICA DE VERIFICACIÓN ===
function verificarHuella(huellaId) {
  const query = `SELECT * FROM Empleados WHERE huella_id = ?`;

  db.get(query, [huellaId], (err, empleado) => {
    if (err) return console.error("❌ Error en consulta:", err.message);

    if (empleado) {
      const nombre = empleado.nombre;
      const empleadoId = empleado.id;
      console.log("✅ Acceso autorizado:", nombre);

      // Insertar acceso
      db.run(`INSERT INTO Accesos (empleado_id) VALUES (?)`, [empleadoId], (err) => {
        if (err) return console.error("❌ Error al registrar acceso:", err.message);
        console.log("🗂️ Acceso registrado en BD.");
      });

      // Enviar al cliente
      enviarATodosClientes(`✅ Acceso autorizado: ${nombre}`);
    } else {
      console.log("❌ Acceso denegado");
      enviarATodosClientes("❌ Acceso denegado: huella no registrada");
    }
  });
}

// === ENVIAR A TODOS LOS CLIENTES CONECTADOS ===
function enviarATodosClientes(mensaje) {
  wss.clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(mensaje);
    }
  });
}

// === INICIAR SERVIDOR ===
const PORT = 3000;
server.listen(PORT, () => {
  console.log(`🌐 Servidor activo en http://localhost:${PORT}`);
});
