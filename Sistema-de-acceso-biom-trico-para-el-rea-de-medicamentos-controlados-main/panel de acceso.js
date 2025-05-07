const empleadosAutorizados = ["EMP001", "EMP003"];

function verificarAcceso() {
  const input = document.getElementById("empleadoId").value.trim().toUpperCase();
  const resultado = document.getElementById("resultado");
  const cajas = document.querySelectorAll("#listaEmpleados .caja");

  let autorizado = empleadosAutorizados.includes(input);

  cajas.forEach(div => {
    div.classList.remove("verde", "rojo");
  });

  cajas.forEach(div => {
    if (div.dataset.id === input) {
      div.classList.add(autorizado ? "verde" : "rojo");
    }
  });

  if (autorizado) {
    resultado.textContent = "Acceso autorizado. ¡Bienvenido!";
    document.body.className = "autorizado";
  } else {
    resultado.textContent = "Acceso denegado. ID no autorizado.";
    document.body.className = "no-autorizado";
  }
}
