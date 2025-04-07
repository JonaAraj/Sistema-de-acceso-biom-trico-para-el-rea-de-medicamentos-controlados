const empleadosAutorizados = ["EMP001", "EMP002", "EMP003", "EMP004"];

                    function verificarAcceso() {
                      const input = document.getElementById("empleadoId").value.trim().toUpperCase();
                      const resultado = document.getElementById("resultado");
                
                      if (empleadosAutorizados.includes(input)) {
                        resultado.textContent = "Acceso autorizado. ¡Bienvenido!";
                        document.body.className = "autorizado";

                      } else {
                        resultado.textContent = "Acceso denegado. ID no autorizado.";
                        document.body.className = "no-autorizado";
                      }
                    }