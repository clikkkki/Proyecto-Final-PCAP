// Envolvemos todo el código dentro de una función principal
function bloqueoCamposFormulario() {
    // Referenciamos el selector 'tipo' y los campos de texto a bloquear
    const tipoSelector = document.querySelector('select[name="tipo"]');
    const campoTemporadas = document.querySelector('input[name="nTemporadas"]');
    const campoCapitulos = document.querySelector('input[name="capitulosTemporada"]');

    // Función para habilitar o deshabilitar los campos
    function alternarCampos() {
        const tipoSeleccionado = tipoSelector.value; // Obtenemos el valor seleccionado del <select>

        if (tipoSeleccionado === "Película") {
            // Si es "Película", deshabilitamos los campos de texto relacionados con "Serie"
            campoTemporadas.disabled = true;
            campoCapitulos.disabled = true;

            // Limpiamos los valores de los campos para evitar datos incorrectos
            campoTemporadas.value = "";
            campoCapitulos.value = "";
        } else if (tipoSeleccionado === "Serie") {
            // Si es "Serie", habilitamos los campos de texto
            campoTemporadas.disabled = false;
            campoCapitulos.disabled = false;
        }
    }

    // Asignamos el evento 'change' al selector para detectar cambios en tiempo real
    tipoSelector.addEventListener("change", alternarCampos);

    // Llamamos a la función una vez para establecer el estado inicial (por si el formulario carga con valores predeterminados)
    alternarCampos();
}

// Llamamos a la función principal al cargar la página
// Esto garantiza que el script se ejecute solo después de que el DOM esté completamente cargado
document.addEventListener("DOMContentLoaded", bloqueoCamposFormulario);
