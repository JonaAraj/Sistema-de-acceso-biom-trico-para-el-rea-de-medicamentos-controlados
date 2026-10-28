let medicamentos = [];

function mostrarMedicamentos(busqueda = "") {
  const contenedor = document.querySelector(".medicamentos");
  const coincidencias = medicamentos.filter((medicamento) =>
    medicamento.name.toLocaleLowerCase().includes(busqueda.trim().toLocaleLowerCase()),
  );

  contenedor.replaceChildren();
  if (coincidencias.length === 0) {
    contenedor.textContent = busqueda
      ? "No se encontraron medicamentos."
      : "No hay medicamentos registrados.";
    return;
  }

  coincidencias.forEach((medicamento) => {
    const tarjeta = document.createElement("div");
    tarjeta.className = "caja-medicamento";
    tarjeta.textContent = `${medicamento.name} (${medicamento.stock} piezas)`;
    contenedor.append(tarjeta);
  });
}

function mostrarSugerencias(busqueda) {
  const lista = document.querySelector(".contenedor-result");
  const barra = document.querySelector(".barra-busqueda");
  const termino = busqueda.trim().toLocaleLowerCase();
  lista.replaceChildren();

  if (!termino) {
    barra.classList.remove("active");
    return;
  }

  const coincidencias = medicamentos
    .filter((medicamento) =>
      medicamento.name.toLocaleLowerCase().includes(termino),
    )
    .slice(0, 8);

  coincidencias.forEach((medicamento) => {
    const opcion = document.createElement("li");
    opcion.textContent = medicamento.name;
    opcion.addEventListener("click", () => {
      const entrada = document.getElementById("busquedaMedicamento");
      entrada.value = medicamento.name;
      mostrarMedicamentos(medicamento.name);
      barra.classList.remove("active");
    });
    lista.append(opcion);
  });

  barra.classList.toggle("active", coincidencias.length > 0);
}

async function cargarMedicamentos() {
  const contenedor = document.querySelector(".medicamentos");
  try {
    medicamentos = await window.apiRequest("/medications");
    mostrarMedicamentos();
  } catch (error) {
    contenedor.textContent = `No se pudieron cargar los medicamentos: ${error.message}`;
    console.error("Error al cargar medicamentos:", error);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const entrada = document.getElementById("busquedaMedicamento");
  entrada.addEventListener("input", () => {
    mostrarSugerencias(entrada.value);
    mostrarMedicamentos(entrada.value);
  });

  document
    .getElementById("buscarMedicamento")
    .addEventListener("click", (event) => {
      event.preventDefault();
      mostrarMedicamentos(entrada.value);
      document.querySelector(".barra-busqueda").classList.remove("active");
    });

  void cargarMedicamentos();
});
