const barrabusqueda = document.querySelector('.barra-busqueda')
const inputbarra = barrabusqueda.querySelector('input')
const resultados = document.querySelector('.contenedor-result')
const lupa = document.querySelector('a')

inputbarra.onkeyup = (e) => {
    let userData = e.target.value
    let emptyArray = []
    
    if(userData){
        emptyArray = result.filter(data =>{
            return data
            .toLocaleLowerCase()
            .startsWith(userData.toLocaleLowerCase())
        })
        emptyArray = emptyArray.map(data => {
            return data = `<li>${data}</li>`;
        })
    barrabusqueda.classList.add('active')
    showResult(emptyArray)

        let allList = resultados.querySelectorAll('li');
        allList.forEach(li =>{
            li.setAttribute('onclick','select(this)')
        })
    }else{
        barrabusqueda.classList.remove('active')
    }
}

function select(element){
    let selectUserData = element.textContent
    resultados.value = selectUserData
    
    searchlink.href = `medicamentos.csv${resultados.value}`;
    barrabusqueda.classList.remove('active');
}

const showResult = list => {
    let ListData;
    if (!list.length){
        userValue = inputbarra.value
        ListData = `<li>${userValue}</li>`;
    }else{
        ListData = list.join(' ')
    }
    resultados.innerHTML = ListData;
}

document.addEventListener("DOMContentLoaded", () => {
    const contenedor = document.querySelector(".medicamentos");
  
    fetch("medicamentos tabla.csv")
      .then(response => response.text())
      .then(data => {
        const lines = data.trim().split("\n").slice(1); 
        lines.forEach(line => {
          const cols = line.split(",");
          const nombre = cols[1];         
          const existencia = cols[7];     
  
          const div = document.createElement("div");
          div.classList.add("caja-medicamento");
          div.textContent = `${nombre} (${existencia} piezas)`;
          contenedor.appendChild(div);
        });
      })
      .catch(error => {
        console.error("Error al cargar el CSV:", error);
      });
  });
  