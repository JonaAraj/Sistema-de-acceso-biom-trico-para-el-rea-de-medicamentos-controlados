async function cargarEmpleados() {
  const contenedor = document.getElementById("listaEmpleados");
  contenedor.replaceChildren();

  try {
    const empleados = await window.apiRequest("/employees");
    if (empleados.length === 0) {
      contenedor.textContent = "No hay empleados registrados.";
      return;
    }

    empleados.forEach((empleado) => {
      const tarjeta = document.createElement("div");
      tarjeta.className = `caja ${empleado.authorized ? "verde" : "rojo"}`;
      tarjeta.dataset.id = empleado.id;
      tarjeta.textContent = `${empleado.name} (${empleado.id}) - Acceso ${empleado.authorized ? "autorizado" : "denegado"}`;
      contenedor.append(tarjeta);
    });
  } catch (error) {
    contenedor.textContent = `No se pudieron cargar los empleados: ${error.message}`;
    console.error("Error al cargar empleados:", error);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  void cargarEmpleados();
  window.setInterval(() => void cargarEmpleados(), 5000);
});

window.cargarEmpleados = cargarEmpleados;
