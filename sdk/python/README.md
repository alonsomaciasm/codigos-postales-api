# 🇲🇽 mx-postal-client (Python SDK)

SDK oficial liviano en Python para consumir la **API de Códigos Postales de México**.

## 📦 Instalación Local

```bash
pip install /ruta/a/codigos-postales-api/sdk/python
```

O directamente desde tu repositorio privado de Git:
```bash
pip install git+https://github.com/tu-usuario/codigos-postales-api.git#subdirectory=sdk/python
```

## 🚀 Uso Rápido

```python
from mx_postal_client import MXPostalClient

# Inicializar cliente apuntando al servidor
client = MXPostalClient(base_url="http://localhost:8080")

# 1. Consultar un CP
cp_info = client.get_codigo_postal("01000")
print(cp_info["municipio"]["nombre"]) # Álvaro Obregón

# 2. Validación de Formulario (CP + Colonia)
val = client.get_codigo_postal("01000", colonia="San Ángel")
print(val["validacion"]["coincidencia_exacta"]) # True

# 3. Autocompletado en Tiempo Real
sugerencias = client.autocomplete("010", limit=5)
for s in sugerencias:
    print(s["codigo_postal"], s["municipio_nombre"])

# 4. Búsqueda por Proximidad Geográfica (Lat, Lng)
cercanos = client.buscar_cercanos(lat=19.4326, lng=-99.1332, radio_km=2.0)
```
