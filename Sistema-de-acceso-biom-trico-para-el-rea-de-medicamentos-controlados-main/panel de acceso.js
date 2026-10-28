let ultimoAccesoMostrado = null;
let consultandoAcceso = false;

function mostrarResultadoAcceso(acceso) {
  const resultado = document.getElementById("resultado");
  const persona =
    acceso.employee?.name ||
    acceso.employee_name ||
    (acceso.credential ? `Credencial ${acceso.credential}` : "credencial");
  const estado = acceso.authorized ? "autorizado" : "denegado";

  resultado.textContent = `Acceso ${estado}: ${persona}.`;
  document.body.className = acceso.authorized
    ? "autorizado"
    : "no-autorizado";
}

async function verificarAcceso() {
  const entrada = document.getElementById("empleadoId");
  const empleadoId = entrada.value.trim().toUpperCase();
  if (!empleadoId) return;

  try {
    const acceso = await window.apiRequest("/access/verify", {
      method: "POST",
      body: JSON.stringify({ employee_id: empleadoId }),
    });
    ultimoAccesoMostrado = acceso.access_id;
    mostrarResultadoAcceso(acceso);
    await window.cargarEmpleados();
  } catch (error) {
    const resultado = document.getElementById("resultado");
    resultado.textContent = `No se pudo verificar el acceso: ${error.message}`;
    document.body.className = "no-autorizado";
    console.error("Error al verificar acceso:", error);
  }
}

async function consultarUltimoAcceso() {
  if (consultandoAcceso) return;
  consultandoAcceso = true;
  try {
    const accesos = await window.apiRequest("/accesses?limit=1");
    if (accesos.length && accesos[0].id !== ultimoAccesoMostrado) {
      ultimoAccesoMostrado = accesos[0].id;
      mostrarResultadoAcceso(accesos[0]);
      await window.cargarEmpleados();
    }
  } catch (error) {
    console.error("Error al consultar el último acceso:", error);
  } finally {
    consultandoAcceso = false;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document
    .getElementById("verificarAcceso")
    .addEventListener("click", () => void verificarAcceso());
  document.getElementById("empleadoId").addEventListener("keydown", (event) => {
    if (event.key === "Enter") void verificarAcceso();
  });
  void consultarUltimoAcceso();
  window.setInterval(() => void consultarUltimoAcceso(), 1500);
});
