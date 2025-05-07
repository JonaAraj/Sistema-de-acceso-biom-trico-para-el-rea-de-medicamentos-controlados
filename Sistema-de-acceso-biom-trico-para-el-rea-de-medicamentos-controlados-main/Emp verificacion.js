document.addEventListener("DOMContentLoaded", () => {
  const empleados = [
    { id: "EMP001", nombre: "Carlos López", autorizado: true },
    { id: "EMP002", nombre: "Ana Torres", autorizado: false },
    { id: "EMP003", nombre: "Luis Ramírez", autorizado: true },
    { id: "EMP004", nombre: "Marta Díaz", autorizado: false }
  ];

  const contenedor = document.getElementById("listaEmpleados");

  empleados.forEach(emp => {
    const div = document.createElement("div");
    div.classList.add("caja");
    div.dataset.id = emp.id; // Guarda el ID en el elemento
    div.textContent = `${emp.nombre} (${emp.id})`;
    contenedor.appendChild(div);
  });
});
