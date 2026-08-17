# 📜 Contrato de API y Especificación Técnica (API Contract)

**API de Códigos Postales de México (SEPOMEX / datos.gob.mx)**  
**Versión:** `1.0.0`  
**Licencia de Datos:** Creative Commons Attribution 4.0 International (CC BY 4.0)

---

## 📋 Tabla de Contenidos
1. [Información General & Base URL](#1-información-general--base-url)
2. [Cláusula de Atribución Legal Obligatoria](#2-cláusula-de-atribución-legal-obligatoria)
3. [Esquema de Autenticación & Seguridad](#3-esquema-de-autenticación--seguridad)
4. [Control de Tasa de Peticiones (Rate Limiting)](#4-control-de-tasa-de-peticiones-rate-limiting)
5. [Estructura Estándar de Manejo de Errores (RFC 7807)](#5-estructura-estándar-de-manejo-de-errores-rfc-7807)
6. [Catálogo Completo de Endpoints](#6-catálogo-completo-de-endpoints)
   - [6.1. Informaciones & Monitoreo](#61-informaciones--monitoreo)
   - [6.2. Autenticación & Tokens](#62-autenticación--tokens)
   - [6.3. Códigos Postales & Asentamientos](#63-códigos-postales--asentamientos)
   - [6.4. Estados & Municipios](#64-estados--municipios)
7. [Clientes SDK Oficiales (mx-postal-client)](#7-clientes-sdk-oficiales-mx-postal-client)

---

## 1. Información General & Base URL

- **URL Base local:** `http://localhost:8000`
- **Prefijo API v1:** `/api/v1`
- **Documentación Swagger UI:** `http://localhost:8000/docs`
- **Documentación ReDoc:** `http://localhost:8000/redoc`
- **Formato de Petición/Respuesta:** JSON (`application/json`) con codificación UTF-8.

---

## 2. Cláusula de Atribución Legal Obligatoria

Conforme a la licencia **CC BY 4.0**, toda aplicación, sistema o producto comercial/no comercial que consuma esta API debe incluir la siguiente mención en su documentación o términos del servicio:

> *"Esta API utiliza y procesa información geográfica y de códigos postales proveniente del catálogo oficial publicado por el Servicio Postal Mexicano (SEPOMEX) a través de datos.gob.mx bajo la licencia Creative Commons Attribution 4.0 International."*

---

## 3. Esquema de Autenticación & Seguridad

La API soporta un esquema híbrido configurable mediante la variable `REQUIRE_AUTH` en el archivo `.env`:

### 3.1. Modo Público (`REQUIRE_AUTH=False`, por defecto)
Las consultas a los endpoints de la API son abiertas sin requerir tokens. Se aplica control de Rate Limiting por dirección IP.

### 3.2. Modo Protegido Empresarial (`REQUIRE_AUTH=True`)
Cada petición a endpoints protegidos debe incluir una de las siguientes cabeceras HTTP:

1. **Autenticación por API Key:**
   ```http
   X-API-Key: key-dev-12345
   ```
2. **Autenticación por Token JWT:**
   ```http
   Authorization: Bearer <tu_jwt_access_token>
   ```

### 3.3. Headers de Seguridad OWASP Aplicados
Todas las respuestas HTTP inyectan automáticamente los siguientes headers de protección:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `X-Correlation-ID: req-<uuid>` (Identificador único para trazabilidad de logs).

### 3.4. Protección Contra Ataques de Agotamiento de Memoria (Payload Size Limit)
- **Middleware:** `RequestBodyLimitMiddleware`
- **Límite Máximo Global de Payload:** `1 MB (1,048,576 bytes)` por cuerpo de solicitud `POST/PUT`.
- **Comportamiento:** Si un cliente envía datos excesivos en el cuerpo de la petición, el servidor aborta la conexión de inmediato respondiendo **`413 Payload Too Large`** antes de consumir RAM intentando procesar la solicitud.
- **Límite de Parámetros Query:** Todos los parámetros de texto `GET` (`query`, `colonia`, `estado`) están restringidos a un máximo de `100` caracteres (`max_length=100`) preveniendo ataques de sobrecarga de CPU por Regex o SQLite FTS5.

---

## 4. Control de Tasa de Peticiones (Rate Limiting)

- **Límite Estándar:** `120 peticiones por minuto por cliente/IP`.
- Si se excede este umbral, el servidor responderá inmediatamente con código HTTP **`429 Too Many Requests`**.

---

## 5. Estructura Estándar de Manejo de Errores (RFC 7807)

Todas las respuestas de error utilizan una estructura JSON unificada con el formato RFC 7807 (Problem Details):

```json
{
  "error": {
    "code": "CODIGO_DE_ERROR",
    "message": "Descripción clara del error en español.",
    "timestamp": "2026-08-16T13:43:00.000000+00:00",
    "correlation_id": "req-8f7a6b5c4d3e",
    "path": "/api/v1/codigo-postal/99999"
  }
}
```

### Tabla de Códigos de Error HTTP Empleados

| Código HTTP | Nombre del Código (`error.code`) | Descripción / Causa |
| :---: | :--- | :--- |
| **`400`** | `BAD_REQUEST` | Petición mal formada o parámetros inconsistentes. |
| **`401`** | `UNAUTHORIZED` | Credenciales de autenticación ausentes, expiradas o inválidas. |
| **`404`** | `NOT_FOUND` | El código postal o recurso solicitado no existe en SEPOMEX. |
| **`422`** | `VALIDATION_ERROR` | Error de validación de entrada (ej. CP no tiene 5 dígitos numéricos). |
| **`429`** | `RATE_LIMIT_EXCEEDED` | Ha superado el límite de 120 peticiones por minuto. |
| **`500`** | `INTERNAL_SERVER_ERROR` | Error interno del servidor. No expone detalles sensibles de BD. |

---

## 6. Catálogo Completo de Endpoints

### 6.1. Informaciones & Monitoreo

#### `GET /`
Retorna información general de la API, endpoints de documentación y cláusula de atribución legal.

- **Headers:** Ninguno.
- **Respuesta `200 OK`:**
```json
{
  "name": "API Códigos Postales de México",
  "version": "1.0.0",
  "docs": "/docs",
  "attribution": {
    "text": "Esta API utiliza y procesa información geográfica...",
    "license": "https://creativecommons.org/licenses/by/4.0/",
    "source": "https://datos.gob.mx"
  }
}
```

#### `GET /health`
Endpoint de salud (*Healthcheck*) con verificación activa en tiempo real de la base de datos (`SELECT 1`).
Utilizado por Docker / Kubernetes para monitorear la salud y disponibilidad del servicio.

- **Respuesta `200 OK` (Servicio Saludable):**
```json
{
  "status": "ok",
  "service": "API Códigos Postales de México",
  "database": "connected",
  "timestamp": "2026-08-16T13:51:00.000000+00:00"
}
```
- **Respuesta `503 Service Unavailable` (Fallo en Base de Datos):**
```json
{
  "status": "error",
  "service": "API Códigos Postales de México",
  "database": "disconnected",
  "detail": "Error de conexión a la base de datos",
  "timestamp": "2026-08-16T13:51:00.000000+00:00"
}
```

#### `GET /api/v1/attribution`
Retorna la cláusula legal completa requerida por CC BY 4.0.

- **Respuesta `200 OK`:**
```json
{
  "mensaje": "Esta API utiliza y procesa información geográfica y de códigos postales proveniente del catálogo oficial publicado por el Servicio Postal Mexicano (SEPOMEX) a través de datos.gob.mx bajo la licencia Creative Commons Attribution 4.0 International.",
  "licencia": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
  "url_licencia": "https://creativecommons.org/licenses/by/4.0/",
  "fuente_oficial": "https://datos.gob.mx"
}
```

---

### 6.2. Autenticación & Tokens

#### `POST /api/v1/auth/token`
Genera un Token de acceso JWT con vigencia configurable (24 horas por defecto) utilizando una `X-API-Key` autorizada.

- **Headers:**
  - `X-API-Key` *(string, obligatorio)*: API Key asignada. Ej: `key-dev-12345`.
- **Respuesta `200 OK`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in_hours": 24
}
```
- **Errores:**
  - `401 UNAUTHORIZED`: `X-API-Key` no enviada o no autorizada.

---

### 6.3. Códigos Postales & Asentamientos

#### `GET /api/v1/codigo-postal/{cp}`
Consulta la información geográfica completa de un Código Postal de 5 dígitos. Opcionalmente realiza validación cruzada si se envían parámetros de formulario.

- **Parámetros Path:**
  - `cp` *(string, obligatorio, regex: `^[0-9]{5}$`)*: Código postal de 5 dígitos. Ej: `01000`, `64000`.
- **Parámetros Query (Opcionales para Validación Cruzada):**
  - `colonia` *(string, opcional)*: Nombre de la colonia a validar contra el CP. Ej: `San Ángel`.
  - `estado` *(string, opcional)*: Nombre o clave del estado a validar. Ej: `Ciudad de México`.
  - `municipio` *(string, opcional)*: Nombre o clave del municipio a validar. Ej: `Álvaro Obregón`.
- **Headers:**
  - `X-API-Key` o `Authorization: Bearer <token>` *(Solo si `REQUIRE_AUTH=True`)*.

- **Respuesta `200 OK` (Con Validación Activada):**
```json
{
  "codigo_postal": "01000",
  "estado": {
    "clave_estado": "09",
    "nombre": "Ciudad de México",
    "nombre_sat": "CIUDAD DE MEXICO"
  },
  "municipio": {
    "clave_municipio": "010",
    "nombre": "Álvaro Obregón",
    "nombre_sat": "ALVARO OBREGON"
  },
  "ciudad": "Ciudad de México",
  "asentamientos": [
    {
      "id": 1,
      "nombre": "San Ángel",
      "nombre_sat": "SAN ANGEL",
      "tipo_asentamiento": "Colonia",
      "zona": "Urbano",
      "codigo_postal": "01000",
      "ciudad": "Ciudad de México",
      "clave_estado": "09",
      "clave_municipio": "010"
    }
  ],
  "validacion": {
    "es_valido": true,
    "match_colonia": true,
    "match_estado": true,
    "match_municipio": true,
    "coincidencia_exacta": true,
    "mensaje": "Coincidencia exacta de formulario válida."
  }
}
```
- **Errores:**
  - `404 NOT_FOUND`: El Código Postal no existe en SEPOMEX.
  - `422 VALIDATION_ERROR`: El código postal no cumple el formato de 5 dígitos numéricos.

---

#### `POST /api/v1/codigo-postal/batch-validate`
Recibe un arreglo (JSON Array) de hasta 100 solicitudes de formulario/direcciones para normalización y validación masiva en lote en una sola llamada HTTP.

- **Body Request (`application/json`):**
```json
[
  { "id_externo": "CUST-001", "codigo_postal": "01000", "colonia": "San Ángel", "estado": "CDMX" },
  { "id_externo": "CUST-002", "codigo_postal": "99999", "colonia": "Desconocida" }
]
```

- **Respuesta `200 OK`:**
```json
[
  {
    "id_externo": "CUST-001",
    "codigo_postal": "01000",
    "existe_cp": true,
    "validacion": {
      "es_valido": true,
      "match_colonia": true,
      "match_estado": true,
      "coincidencia_exacta": true,
      "mensaje": "Coincidencia exacta de formulario válida."
    },
    "oficial": {
      "estado": "Ciudad de México",
      "estado_sat": "CIUDAD DE MEXICO",
      "municipio": "Álvaro Obregón",
      "municipio_sat": "ALVARO OBREGON",
      "asentamientos": ["San Ángel"]
    }
  },
  {
    "id_externo": "CUST-002",
    "codigo_postal": "99999",
    "existe_cp": false,
    "validacion": {
      "es_valido": false,
      "mensaje": "El código postal 99999 no existe en el catálogo SEPOMEX."
    },
    "oficial": null
  }
]
```

#### `GET /api/v1/codigo-postal/cercanos`
Busca los asentamientos y códigos postales más cercanos a un punto geográfico (Latitud, Longitud) dentro de un radio determinado en kilómetros utilizando filtrado Bounding Box e índices B-Tree en SQLite + Fórmula de Haversine.

- **Parámetros Query:**
  - `lat` *(float, obligatorio, -90.0 a 90.0)*: Latitud del punto (ej. `19.4326`).
  - `lng` *(float, obligatorio, -180.0 a 180.0)*: Longitud del punto (ej. `-99.1332`).
  - `radio_km` *(float, opcional, min: 0.1, máx: 50.0, defecto: 5.0)*: Radio de búsqueda en kilómetros.
  - `limit` *(integer, opcional, min: 1, máx: 50, defecto: 10)*: Límite máximo de asentamientos a retornar.

- **Respuesta `200 OK`:**
```json
[
  {
    "id": 1,
    "nombre": "San Ángel",
    "tipo_asentamiento": "Colonia",
    "zona": "Urbano",
    "codigo_postal": "01000",
    "ciudad": "Ciudad de México",
    "clave_estado": "09",
    "clave_municipio": "010",
    "latitud": 19.4326,
    "longitud": -99.1332,
    "distancia_km": 0.0
  },
  {
    "id": 2,
    "nombre": "Los Alpes",
    "tipo_asentamiento": "Colonia",
    "zona": "Urbano",
    "codigo_postal": "01010",
    "ciudad": "Ciudad de México",
    "clave_estado": "09",
    "clave_municipio": "010",
    "latitud": 19.4346,
    "longitud": -99.1312,
    "distancia_km": 0.283
  }
]
```

---

#### `GET /api/v1/asentamientos`
Búsqueda avanzada de texto FTS5 (insensible a acentos), filtros combinables y paginación estructurada.

- **Parámetros Query:**
  - `query` *(string, opcional, min_length: 2)*: Búsqueda libre por texto (ej. `juarez`, `san angel`, `polanco`).
  - `clave_estado` *(string, opcional)*: Clave del estado (ej. `09`).
  - `clave_municipio` *(string, opcional)*: Clave del municipio (ej. `010`).
  - `tipo_asentamiento` *(string, opcional)*: Tipo (ej. `Colonia`, `Barrio`, `Fraccionamiento`).
  - `zona` *(string, opcional)*: `Urbano` o `Rural`.
  - `page` *(integer, opcional, min: 1, defecto: 1)*: Número de página.
  - `limit` *(integer, opcional, min: 1, máx: 1000, defecto: 20)*: Registros por página.
  - `format` *(string, opcional)*: Formato de exportación directa (`csv` o `excel`). Descarga en streaming de archivo `.csv`.

- **Respuesta `200 OK` (Modo JSON Estándar):**
```json
{
  "total_records": 154,
  "total_pages": 31,
  "current_page": 1,
  "limit": 5,
  "data": [
    {
      "id": 15,
      "nombre": "Juárez",
      "tipo_asentamiento": "Colonia",
      "zona": "Urbano",
      "codigo_postal": "06600",
      "ciudad": "Ciudad de México",
      "clave_estado": "09",
      "clave_municipio": "015"
    }
  ]
}
```

---

#### `GET /api/v1/asentamientos/search`
Búsqueda rápida de asentamientos por nombre con insensibilidad a acentos.

- **Parámetros Query:**
  - `query` *(string, obligatorio, min_length: 2)*: Término de búsqueda. Ej: `juarez`, `merida`.
  - `limit` *(integer, opcional, min: 1, máx: 100, defecto: 20)*: Límite de resultados.

- **Respuesta `200 OK`:**
```json
[
  {
    "id": 15,
    "nombre": "Juárez",
    "tipo_asentamiento": "Colonia",
    "zona": "Urbano",
    "codigo_postal": "06600",
    "ciudad": "Ciudad de México",
    "clave_estado": "09",
    "clave_municipio": "015"
  }
]
```

---

#### `GET /api/v1/codigo-postal/autocomplete`
Autocompletado de Códigos Postales por prefijo numérico (2 a 5 dígitos) ideal para integraciones con formularios web y apps móviles.

- **Parámetros Query:**
  - `prefix` *(string, obligatorio, min_length: 2, max_length: 5, regex: `^[0-9]{2,5}$`)*: Prefijo numérico. Ej. `01`, `010`.
  - `limit` *(integer, opcional, min: 1, máx: 50, defecto: 10)*: Límite de sugerencias.

- **Respuesta `200 OK`:**
```json
[
  {
    "codigo_postal": "01000",
    "estado_nombre": "Ciudad de México",
    "municipio_nombre": "Álvaro Obregón",
    "total_asentamientos": 1
  },
  {
    "codigo_postal": "01010",
    "estado_nombre": "Ciudad de México",
    "municipio_nombre": "Álvaro Obregón",
    "total_asentamientos": 1
  }
]
```

---

#### `GET /api/v1/stats`
Retorna el resumen métrico y estadístico global del catálogo de SEPOMEX cargado en el sistema.

- **Respuesta `200 OK`:**
```json
{
  "total_codigos_postales": 32800,
  "total_asentamientos": 148500,
  "total_estados": 32,
  "total_municipios": 2475,
  "tipos_asentamiento_conteo": {
    "Colonia": 65000,
    "Barrio": 12000,
    "Ejido": 10500,
    "Fraccionamiento": 9800
  },
  "zonas_conteo": {
    "Urbano": 95000,
    "Rural": 53500
  }
}
```

---

#### `GET /api/v1/codigo-postal/{cp}/geojson`
Exportación de coordenadas y colonias asociadas a un Código Postal en estándar internacional **GeoJSON (FeatureCollection)** para Mapbox, Leaflet, Google Maps y GIS.

- **Parámetros Path:**
  - `cp` *(string, obligatorio, regex: `^[0-9]{5}$`)*: Código postal de 5 dígitos (ej. `01000`).

- **Respuesta `200 OK`:**
```json
{
  "type": "FeatureCollection",
  "codigo_postal": "01000",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-99.1332, 19.4326]
      },
      "properties": {
        "id": 1,
        "codigo_postal": "01000",
        "nombre": "San Ángel",
        "nombre_sat": "SAN ANGEL",
        "tipo_asentamiento": "Colonia",
        "zona": "Urbano",
        "ciudad": "Ciudad de México",
        "estado": "Ciudad de México",
        "municipio": "Álvaro Obregón"
      }
    }
  ]
}
```

---

#### `GET /metrics`
Endpoint de monitoreo y observabilidad en tiempo real que expone métricas en formato estándar **Prometheus** (latencias p50/p95/p99, throughput de peticiones, códigos de estado HTTP y errores).

- **Headers:** Ninguno (utilizado por Prometheus / Grafana / Datadog).
- **Respuesta `200 OK` (`text/plain`):**
```text
# HELP http_requests_total Total number of HTTP requests
# TYPE http_requests_total counter
http_requests_total{handler="/api/v1/codigo-postal/{cp}",method="GET",status="200"} 1420.0
```

---

#### `GET /dashboard`
Sirve la interfaz web ejecutiva e interactiva de observabilidad, estadísticas del catálogo SEPOMEX, mapa GeoJSON multicapa y terminal de logs de auditoría a todo lo ancho de la página.

- **Headers:** Ninguno.
- **Respuesta `200 OK` (`text/html`):** Plantilla HTML5 responsive con widgets Chart.js y Leaflet.js.

---

#### `GET /api/v1/logs`
Obtiene los eventos de auditoría y registros de log del servidor en tiempo real en formato estructurado JSON.

- **Parámetros Query:**
  - `limit` *(integer, opcional, min: 1, máx: 200, defecto: 50)*: Cantidad de registros a retornar.
  - `level` *(string, opcional)*: Nivel de log a filtrar (`INFO`, `WARNING`, `ERROR`).

- **Respuesta `200 OK`:**
```json
{
  "total_entries": 2,
  "limit": 50,
  "logs": [
    {
      "timestamp": "2026-08-17 05:33:43.431880-06:00",
      "level": "INFO",
      "message": "HTTP GET /api/v1/codigo-postal/01000/geojson - Status: 200 - Latency: 4.65ms - IP: 127.0.0.1 - CID: req-07584d94d107",
      "module": "audit_logging"
    }
  ]
}
```

---

### 6.4. Estados & Municipios

#### `GET /api/v1/estados`
Retorna el catálogo completo de las 32 Entidades Federativas de México (incluye campo `nombre_sat` compatible con SAT/CFDI 4.0).

- **Respuesta `200 OK`:**
```json
[
  {
    "clave_estado": "01",
    "nombre": "Aguascalientes",
    "nombre_sat": "AGUASCALIENTES"
  },
  {
    "clave_estado": "09",
    "nombre": "Ciudad de México",
    "nombre_sat": "CIUDAD DE MEXICO"
  }
]
```

---

#### `GET /api/v1/estados/{c_estado}/municipios`
Retorna los municipios o alcaldías asociados a una clave de estado (incluye `nombre_sat`).

- **Parámetros Path:**
  - `c_estado` *(string, obligatorio)*: Clave de 2 dígitos del estado. Ej: `09` (CDMX), `19` (NL).

- **Respuesta `200 OK`:**
```json
[
  {
    "clave_municipio": "039",
    "nombre": "Monterrey",
    "nombre_sat": "MONTERREY"
  },
  {
    "clave_municipio": "046",
    "nombre": "San Pedro Garza García",
    "nombre_sat": "SAN PEDRO GARZA GARCIA"
  }
]
```

#### `GET /api/v1/estados/{c_estado}/geojson`
Exportación de la colección de capas geográficas completa (`FeatureCollection`) de todos los asentamientos con coordenadas de un Estado.

- **Parámetros Path:**
  - `c_estado` *(string, obligatorio)*: Clave de 2 dígitos del estado (ej. `09` para CDMX).
- **Respuesta `200 OK` (`application/json`):** Colección estándar GeoJSON.

---

#### `GET /api/v1/estados/{c_estado}/pdf`
Genera y descarga en tiempo real una ficha técnica ejecutiva en formato **PDF** con el desglose de municipios y atribución legal.

- **Parámetros Path:**
  - `c_estado` *(string, obligatorio)*: Clave del estado (ej. `09` para CDMX, `19` para NL).
- **Parámetros Query (Personalización Opcional):**
  - `titulo` *(string, opcional)*: Título del documento. Defecto: `Reporte Geográfico Ejecutivo - SEPOMEX`.
  - `subtitulo` *(string, opcional)*: Subtítulo del documento. Defecto: `Ficha Técnica Oficial de Entidad Federativa`.
  - `logo_url` *(string, opcional)*: URL HTTP/HTTPS del logotipo de la empresa. Si no se provee o no es accesible, utiliza un ícono/bandera institucional por defecto.

- **Respuesta `200 OK` (`application/pdf`):** Descarga directa de archivo `reporte_estado_{c_estado}.pdf`.

---

#### `GET /api/v1/estados/{c_estado}/municipios/{c_municipio}`
Consulta el detalle completo de un municipio incluyendo la totalidad de sus Códigos Postales y Colonias.

- **Parámetros Path:**
  - `c_estado` *(string, obligatorio)*: Clave de 2 dígitos del estado (ej. `09`).
  - `c_municipio` *(string, obligatorio)*: Clave de 3 dígitos del municipio (ej. `010`).

- **Respuesta `200 OK`:**
```json
{
  "clave_estado": "09",
  "estado_nombre": "Ciudad de México",
  "clave_municipio": "010",
  "municipio_nombre": "Álvaro Obregón",
  "total_codigos_postales": 85,
  "codigos_postales": ["01000", "01010", "01020"],
  "total_asentamientos": 230,
  "asentamientos": [
    {
      "id": 1,
      "nombre": "San Ángel",
      "nombre_sat": "SAN ANGEL",
      "tipo_asentamiento": "Colonia",
      "zona": "Urbano",
      "codigo_postal": "01000",
      "ciudad": "Ciudad de México",
      "clave_estado": "09",
      "clave_municipio": "010"
    }
  ]
}
```

---

## 7. Clientes SDK Oficiales (`mx-postal-client`)

El repositorio incluye dos SDKs listos para consumo local o integración en proyectos externos:

- **SDK Python (`sdk/python/README.md`):** Paquete cliente basado en `httpx` e `pydantic`. Soporta métodos síncronos, validación cruzada y autocompletado.
- **SDK TypeScript / Node.js (`sdk/typescript/README.md`):** Paquete cliente basado en `fetch` e interfaces fuertemente tipadas en TypeScript. Compilado en la carpeta `/dist`.

