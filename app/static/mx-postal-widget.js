/**
 * 🇲🇽 MX-Postal-Widget (Web Component / Auto-Fill Widget)
 * Permite autocompletar formularios HTML conectándose automáticamente a la API de Códigos Postales.
 * 
 * Uso:
 * <input type="text" data-mx-postal="cp" placeholder="Código Postal">
 * <select data-mx-postal="colonia"></select>
 * <input type="text" data-mx-postal="municipio">
 * <input type="text" data-mx-postal="estado">
 */
(function() {
  'use strict';

  document.addEventListener('DOMContentLoaded', function() {
    var cpInput = document.querySelector('[data-mx-postal="cp"]');
    if (!cpInput) return;

    var coloniaSelect = document.querySelector('[data-mx-postal="colonia"]');
    var municipioInput = document.querySelector('[data-mx-postal="municipio"]');
    var estadoInput = document.querySelector('[data-mx-postal="estado"]');
    var ciudadInput = document.querySelector('[data-mx-postal="ciudad"]');

    // Determinar la URL base de la API desde el atributo del script o el host actual
    var scriptTag = document.querySelector('script[src*="mx-postal-widget.js"]');
    var baseUrl = (scriptTag && scriptTag.getAttribute('data-api-base')) || '';

    cpInput.addEventListener('input', function(e) {
      var cp = e.target.value.trim();
      if (/^\d{5}$/.test(cp)) {
        fetchCPData(cp);
      }
    });

    function fetchCPData(cp) {
      var url = baseUrl + '/api/v1/codigo-postal/' + cp;
      fetch(url)
        .then(function(res) {
          if (!res.ok) throw new Error('CP no encontrado');
          return res.json();
        })
        .then(function(data) {
          if (estadoInput) {
            if (estadoInput.tagName === 'SELECT') {
              setSelectedOption(estadoInput, data.estado.nombre);
            } else {
              estadoInput.value = data.estado.nombre;
            }
          }

          if (municipioInput) {
            if (municipioInput.tagName === 'SELECT') {
              setSelectedOption(municipioInput, data.municipio.nombre);
            } else {
              municipioInput.value = data.municipio.nombre;
            }
          }

          if (ciudadInput) {
            ciudadInput.value = data.ciudad || data.municipio.nombre;
          }

          if (coloniaSelect) {
            coloniaSelect.innerHTML = '';
            data.asentamientos.forEach(function(asentamiento) {
              var opt = document.createElement('option');
              opt.value = asentamiento.nombre;
              opt.textContent = asentamiento.nombre + ' (' + asentamiento.tipo_asentamiento + ')';
              coloniaSelect.appendChild(opt);
            });
          }

          // Disparar evento personalizado
          var event = new CustomEvent('mx-postal-loaded', { detail: data });
          cpInput.dispatchEvent(event);
        })
        .catch(function(err) {
          console.warn('MXPostalWidget:', err.message);
        });
    }

    function setSelectedOption(select, value) {
      for (var i = 0; i < select.options.length; i++) {
        if (select.options[i].text.toLowerCase().includes(value.toLowerCase())) {
          select.selectedIndex = i;
          break;
        }
      }
    }
  });
})();
