/* let result = [
    'medicamento 1', //cambiar por medicamentos y contenido
    'paracetamol',
    'aspirina',
    'ibuprofeno',
    'amoxicilina',
    'ciprofloxacino',
    'azitromicina',
    'cefalexina',
]; */

let result = [];

fetch('medicamentos tabla.csv')
  .then(response => response.text())
  .then(data => {
    const lineas = data.split('\n').slice(1); 
    result = lineas.map(linea => {
        const columnas = linea.split(',');
        return columnas[1] ? columnas[1].trim().toLowerCase() : null;
      }).filter(nombre => nombre); 

    console.log("Medicamentos cargados:", result);
  })
  .catch(error => {
    console.error('Error al cargar el CSV:', error);
  });