# 🇲🇽 mx-postal-client (TypeScript / Node.js SDK)

SDK oficial liviano en TypeScript / JavaScript para consumir la **API de Códigos Postales de México**.

## 📦 Instalación Local

```bash
npm install /ruta/a/codigos-postales-api/sdk/typescript
```

O directamente desde tu repositorio privado de Git:
```bash
npm install git+https://github.com/tu-usuario/codigos-postales-api.git#subdirectory=sdk/typescript
```

## 🚀 Uso Rápido

```typescript
import { MXPostalClient } from 'mx-postal-client';

const client = new MXPostalClient({ baseUrl: 'http://localhost:8080' });

async function run() {
  // 1. Consultar un CP
  const detail = await client.getCodigoPostal('01000');
  console.log(detail.municipio.nombre); // Álvaro Obregón

  // 2. Validación de Formulario (CP + Colonia)
  const val = await client.getCodigoPostal('01000', { colonia: 'San Ángel' });
  console.log(val.validacion?.coincidencia_exacta); // true

  // 3. Autocompletado en Tiempo Real
  const sugerencias = await client.autocomplete('010', 5);
  console.log(sugerencias);
}

run();
```
