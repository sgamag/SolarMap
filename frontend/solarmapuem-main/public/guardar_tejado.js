async function guardarTejadoSeleccionado(feature) {

    const p = feature.properties || {};

    const coords = feature.geometry.coordinates[0];

    let sumaLon = 0;
    let sumaLat = 0;

    coords.forEach(coord => {
        sumaLon += coord[0];
        sumaLat += coord[1];
    });

    const centroLon = sumaLon / coords.length;
    const centroLat = sumaLat / coords.length;

    const datos = {
        lat: centroLat,
        lon: centroLon,
        area_m2: p.area_m2,
        orientation_angle_degrees: p.orientation_angle_degrees,
        orientation_label: p.orientation_label
    };

    try {

        const response = await fetch(
            "http://localhost:8001/seleccionar-tejado",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(datos)
            }
        );

        const resultado = await response.json();

        console.log("Tejado guardado:", resultado);

        alert("Tejado guardado correctamente");

    } catch (err) {

        console.error(err);

        alert("Error guardando tejado");
    }
}