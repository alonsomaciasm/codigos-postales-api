# API de Códigos Postales de México 🇲🇽

API RESTful ultra-rápida construida con **Python 3.12**, **FastAPI**, **SQLite en modo WAL** y **Docker**, diseñada para responder en **< 1 ms** con el catálogo oficial de Códigos Postales, Asentamientos, Municipios y Estados de México.

---

## 📜 Cláusula de Atribución Legal (Obligatoria por CC BY 4.0)

> **Esta API utiliza y procesa información geográfica y de códigos postales proveniente del catálogo oficial publicado por el Servicio Postal Mexicano (SEPOMEX) a través de datos.gob.mx bajo la licencia Creative Commons Attribution 4.0 International.**

---

## 🚀 Características Principales

- **Contrato de API y Especificación:** [docs/api_contract.md](file:///home/alonso/Proyectos/codigos-postales-api/docs/api_contract.md)
- **Velocidad y Desempeño:** Tiempos de respuesta sub-milisegundo con SQLite en modo Write-Ahead Logging (WAL) y serialización `orjson`.
- **Ciberseguridad:** Hardening OWASP, headers de seguridad, Rate Limiting, validación estricta de regex Pydantic v2 y Docker non-root user.
- **Manejo de Errores Enterprise:** Formato RFC 7807 (Problem Details) con `X-Correlation-ID` único por petición.
- **Auditoría & Logging:** Logs en JSON estructurado mediante `loguru` con **rotación diaria a medianoche (`00:00`)**, compresión `.zip` y retención de 30 días.
- **Prevención de Deadlocks:** Conexiones HTTP en modo solo lectura (`mode=ro`) con `PRAGMA busy_timeout=5000;`.
- **Script de Ingesta Automático:** Descarga, limpia (ISO-8859-1 a UTF-8) y puebla la base de datos de manera atómica.

---

## 📦 Instalación y Ejecución Local

### 1. Requisitos Previos
- Python 3.10+
- Virtualenv o Docker

### 2. Configurar entorno e instalar dependencias
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Ejecutar Ingesta de Datos (SEPOMEX / datos.gob.mx)
```bash
python scripts/ingest_sepomex.py
```
*Este comando descargará el archivo `CPdescarga.txt` oficial y generará `sepomex.db` con más de 148,000 asentamientos e índices optimizados.*

### 4. Iniciar Servidor de Desarrollo
```bash
uvicorn app.main:app --reload --port 8000
```
Visita la documentación interactiva en: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🐳 Ejecución con Docker

### Opción A: Docker Build & Run
```bash
docker build -t codigos-postales-api .
docker run -p 8000:8000 codigos-postales-api
```

### Opción B: Docker Compose
```bash
docker-compose up -d
```

---

## 🔐 Autenticación & Rate Limiting (API Key & JWT)

La API cuenta con un esquema de autenticación híbrido configurable desde `.env`:

### 1. Modos de Operación (`REQUIRE_AUTH`)
- **`REQUIRE_AUTH=False` (Modo API Pública, por defecto):** Los endpoints son de acceso libre. El control de peticiones se realiza mediante **Rate Limiting por IP** (120 req/min por defecto).
- **`REQUIRE_AUTH=True` (Modo API Protegida Empresarial):** Requiere que cada petición envíe credenciales válidas en los headers.

### 2. Opciones de Autenticación Soportadas
1. **Header `X-API-Key`:**
   ```bash
   curl -H "X-API-Key: key-dev-12345" http://localhost:8000/api/v1/codigo-postal/01000
   ```
2. **Token JWT Bearer (`Authorization: Bearer <token>`):**
   - Canje de token JWT (válido por 24 horas):
     ```bash
     curl -X POST http://localhost:8000/api/v1/auth/token -H "X-API-Key: key-dev-12345"
     ```
   - Petición con el Token devuelto:
     ```bash
     curl -H "Authorization: Bearer <tu_jwt_token>" http://localhost:8000/api/v1/codigo-postal/01000
     ```

---

## 🛠️ Endpoints Disponibles

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `GET` | `/dashboard` | Dashboard Web interactivo de observabilidad, estadísticas y mapa GeoJSON |
| `GET` | `/api/v1/codigo-postal/{cp}` | Consulta detalle de un CP (incluye `nombre_sat` y validación de formulario opcional `colonia`, `estado`, `municipio`) |
| `POST` | `/api/v1/codigo-postal/batch-validate` | Validación y normalización masiva en lote de hasta 100 direcciones en una sola petición HTTP |
| `GET` | `/api/v1/codigo-postal/{cp}/geojson` | Exportación de coordenadas y colonias en formato estándar GeoJSON (`FeatureCollection`) |
| `GET` | `/api/v1/codigo-postal/autocomplete?prefix=01` | Autocompletado en tiempo real por prefijo de 2 a 5 dígitos |
| `GET` | `/api/v1/codigo-postal/cercanos?lat=19.43&lng=-99.13` | Búsqueda por proximidad geográfica (Haversine + Bounding Box) |
| `GET` | `/api/v1/asentamientos` | Búsqueda FTS5 sin acentos, filtros combinados, paginación y exportación directa (`format=csv`) |
| `GET` | `/api/v1/asentamientos/search?query=juarez` | Búsqueda rápida de asentamientos insensible a acentos |
| `GET` | `/api/v1/estados` | Lista de las 32 entidades federativas (con `nombre_sat`) |
| `GET` | `/api/v1/estados/{c_estado}/municipios` | Municipios por clave de estado |
| `GET` | `/api/v1/estados/{c_estado}/municipios/{c_municipio}` | Detalle completo de municipio con todos sus CPs y colonias |
| `GET` | `/api/v1/estados/{c_estado}/geojson` | Exportación de capas geográficas completas del estado en formato GeoJSON (`FeatureCollection`) |
| `GET` | `/api/v1/estados/{c_estado}/pdf` | Generación y descarga de reporte PDF ejecutivo (parámetros opcionales `titulo`, `subtitulo`, `logo_url`) |
| `GET` | `/static/mx-postal-widget.js` | Widget JavaScript para autocompletado automático de formularios HTML en cliente |
| `GET` | `/api/v1/stats` | Estadísticas métricas y desglose del catálogo SEPOMEX |
| `GET` | `/api/v1/logs` | Registros de auditoría en vivo y eventos del servidor en formato JSON |
| `GET` | `/api/v1/attribution` | Cláusula de Atribución Legal CC BY 4.0 |
| `GET` | `/metrics` | Métricas de monitoreo en estándar Prometheus |
| `GET` | `/health` | Healthcheck para monitoreo Docker/K8s |

---

## 📦 Clientes SDK Oficiales (`mx-postal-client`)

El proyecto incluye dos paquetes clientes SDK livianos para consumir la API fácilmente sin escribir peticiones HTTP manuales:

- **Python SDK (`sdk/python`):**
  ```bash
  pip install ./sdk/python
  ```
  ```python
  from mx_postal_client import MXPostalClient
  client = MXPostalClient(base_url="http://localhost:8080")
  cp_data = client.get_codigo_postal("01000", colonia="San Ángel")
  ```

- **TypeScript / Node.js SDK (`sdk/typescript`):**
  ```bash
  npm install ./sdk/typescript
  ```
  ```typescript
  import { MXPostalClient } from 'mx-postal-client';
  const client = new MXPostalClient({ baseUrl: 'http://localhost:8080' });
  const detail = await client.getCodigoPostal('01000');
  ```

---

## 🤖 Integración con Agentes de IA (Model Context Protocol - MCP)

La API cuenta con un **Servidor MCP oficial** ([`scripts/mcp_server.py`](file:///home/alonso/Proyectos/codigos-postales-api/scripts/mcp_server.py)) que permite a Agentes de IA (Claude Desktop, ChatGPT, Antigravity IDE, LangChain, AutoGPT) consultar e interactuar con la base de datos geográfica oficial de México en lenguaje natural.

### Herramientas Expuestas para IA:
1. `consultar_codigo_postal(cp)`: Retorna la ficha geográfica completa y lista de colonias.
2. `validar_direccion_postal(codigo_postal, colonia, estado, municipio)`: Valida en tiempo real la coincidencia de datos con SEPOMEX.
3. `buscar_asentamientos_por_nombre(nombre_colonia, limite)`: Búsqueda en lenguaje natural por palabras clave.

### Configuración en Claude Desktop / Antigravity IDE (`mcp.json`):
```json
{
  "mcpServers": {
    "mx-postal-codes": {
      "command": "python3",
      "args": ["/ruta/absoluta/a/codigos-postales-api/scripts/mcp_server.py"]
    }
  }
}
```

---

## 🔄 Verificación Automática del Catálogo SEPOMEX

El contenedor ejecuta en segundo plano un planificador mensual asíncrono que comprueba la existencia de novedades en `datos.gob.mx` sin afectar la latencia HTTP (`< 1 ms`).

Para ejecutar manualmente la verificación o forzar la actualización del catálogo dentro del contenedor Docker:
```bash
docker exec codigos_postales_api python3 scripts/check_updates.py --force
```

---

## 🏆 Comparativa con el Estado del Arte (2026)

Comparativa técnica de nuestra solución en relación a las alternativas open-source y servicios comerciales SaaS del mercado actual:

| Dimensión Técnica / Funcionalidad | 🚀 **Este Proyecto** | 🟢 **Tlaloc.sh** | 🐍 **Sepomex-MCP** | ⚡ **go-mexpost** | 💳 **Copomex** |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Arquitectura** | **Self-Hosted (Docker/WAL)** | SaaS Nube | Self-Hosted / Python | Self-Hosted / Go | SaaS Nube |
| **Latencia p99** | **< 0.5 ms (Caché RAM L1)** | ~120 ms | ~15 ms | ~2 ms | ~200 ms |
| **Estándar SAT CFDI 4.0** | ✅ **Nativa (`nombre_sat`)** | ✅ Nativa | ❌ No disponible | ❌ No disponible | ⚠️ Parcial |
| **Validación Masiva Lote (`POST`)** | ✅ **Hasta 100 req/petición** | ❌ No disponible | ❌ No disponible | ❌ No disponible | ❌ No disponible |
| **Vectorial GeoJSON (CP y Estado)** | ✅ **Completo (Point & Bounds)**| ❌ No disponible | ❌ No disponible | ❌ No disponible | ❌ No disponible |
| **Reporte Ejecutivo PDF** | ✅ **Nativo (ReportLab)** | ❌ No disponible | ❌ No disponible | ❌ No disponible | ❌ No disponible |
| **Widget JavaScript Frontend** | ✅ **`mx-postal-widget.js`** | ❌ No disponible | ❌ No disponible | ❌ No disponible | ⚠️ Custom JS |
| **Servidor MCP para Agentes IA** | ✅ **`scripts/mcp_server.py`** | ❌ No disponible | ✅ Incluido | ❌ No disponible | ❌ No disponible |
| **SDKs Oficiales (Python/TS)** | ✅ **`mx-postal-client`** | ❌ Peticiones HTTP | ❌ Peticiones HTTP | ❌ Peticiones HTTP | ❌ Peticiones HTTP |
| **Protección Payload Size (1 MB)** | ✅ **`RequestBodyLimit`** | ⚠️ Desconocido | ❌ No disponible | ⚠️ Nivel Proxy | ⚠️ Nivel Proxy |
| **Costo Operativo** | **$0 USD (Ilimitado)** | Pay-per-lookup | $0 USD | $0 USD | $15-$150 USD/m |

---

## 🔬 Experimentos y Artículo Científico

El repositorio incluye la suite completa de pruebas cuantitativas y el manuscrito formal del artículo científico en la carpeta [`paper_experiments/`](file:///home/alonso/Proyectos/codigos-postales-api/paper_experiments):

- **Manuscrito Académico:** [`paper_experiments/4_graficas_y_manuscrito/articulo_cientifico.md`](file:///home/alonso/Proyectos/codigos-postales-api/paper_experiments/4_graficas_y_manuscrito/articulo_cientifico.md)
- **Fase 1 (Latencia y Lote):** Aceleración de **58.91x** en validación en lote (`POST /batch-validate`).
- **Fase 2 (Normalización SAT):** $F_1$-Score algorítmico del **90.45%** con 100% de precisión en dataset de 1,000 muestras con ruido.
- **Fase 3 (Agentes IA / MCP):** **99.43% de ahorro en tokens** al interoperar vía el Servidor MCP.

---

## 🧪 Ejecutar Pruebas
```bash
pytest
```
