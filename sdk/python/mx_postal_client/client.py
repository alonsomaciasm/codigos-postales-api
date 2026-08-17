import httpx
from typing import Dict, List, Optional, Any

class MXPostalClientError(Exception):
    """Excepción base para errores del SDK mx-postal-client."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}

class MXPostalClient:
    """
    Cliente Python síncrono y asíncrono para consumir la API de Códigos Postales de México.
    """

    def __init__(self, base_url: str = "http://localhost:8080", api_key: Optional[str] = None, token: Optional[str] = None, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {"Accept": "application/json"}

        if api_key:
            self.headers["X-API-Key"] = api_key
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def _get_client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, headers=self.headers, timeout=self.timeout)

    def _handle_response(self, response: httpx.Response) -> Any:
        if response.is_success:
            return response.json()
        
        try:
            error_data = response.json()
        except Exception:
            error_data = {"error": {"message": response.text}}

        msg = error_data.get("error", {}).get("message", f"HTTP Error {response.status_code}")
        raise MXPostalClientError(message=msg, status_code=response.status_code, details=error_data)

    def get_codigo_postal(self, cp: str, colonia: Optional[str] = None, estado: Optional[str] = None, municipio: Optional[str] = None) -> Dict[str, Any]:
        """Consulta un Código Postal de 5 dígitos con opción de validación cruzada."""
        params = {}
        if colonia: params["colonia"] = colonia
        if estado: params["estado"] = estado
        if municipio: params["municipio"] = municipio

        with self._get_client() as client:
            res = client.get(f"/api/v1/codigo-postal/{cp}", params=params)
            return self._handle_response(res)

    def batch_validate(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Valida y normaliza en lote un arreglo de hasta 100 solicitudes de formulario."""
        with self._get_client() as client:
            res = client.post("/api/v1/codigo-postal/batch-validate", json=items)
            return self._handle_response(res)

    def get_geojson(self, cp: str) -> Dict[str, Any]:
        """Obtiene la exportación en estándar GeoJSON (FeatureCollection) para un CP."""
        with self._get_client() as client:
            res = client.get(f"/api/v1/codigo-postal/{cp}/geojson")
            return self._handle_response(res)

    def autocomplete(self, prefix: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Autocompletado de códigos postales por prefijo numérico de 2 a 5 dígitos."""
        with self._get_client() as client:
            res = client.get("/api/v1/codigo-postal/autocomplete", params={"prefix": prefix, "limit": limit})
            return self._handle_response(res)

    def buscar_cercanos(self, lat: float, lng: float, radio_km: float = 5.0, limit: int = 10) -> List[Dict[str, Any]]:
        """Busca asentamientos y CPs cercanos a un punto geográfico (Latitud, Longitud)."""
        with self._get_client() as client:
            res = client.get("/api/v1/codigo-postal/cercanos", params={"lat": lat, "lng": lng, "radio_km": radio_km, "limit": limit})
            return self._handle_response(res)

    def get_asentamientos(self, query: Optional[str] = None, clave_estado: Optional[str] = None, clave_municipio: Optional[str] = None, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """Búsqueda avanzada de asentamientos con filtros y FTS5."""
        params = {"page": page, "limit": limit}
        if query: params["query"] = query
        if clave_estado: params["clave_estado"] = clave_estado
        if clave_municipio: params["clave_municipio"] = clave_municipio

        with self._get_client() as client:
            res = client.get("/api/v1/asentamientos", params=params)
            return self._handle_response(res)

    def get_estados(self) -> List[Dict[str, Any]]:
        """Retorna la lista de las 32 entidades federativas."""
        with self._get_client() as client:
            res = client.get("/api/v1/estados")
            return self._handle_response(res)

    def get_municipios(self, clave_estado: str) -> List[Dict[str, Any]]:
        """Retorna los municipios asociados a un estado."""
        with self._get_client() as client:
            res = client.get(f"/api/v1/estados/{clave_estado}/municipios")
            return self._handle_response(res)

    def get_estado_geojson(self, clave_estado: str) -> Dict[str, Any]:
        """Obtiene la exportación de capa geográfica completa GeoJSON para un Estado."""
        with self._get_client() as client:
            res = client.get(f"/api/v1/estados/{clave_estado}/geojson")
            return self._handle_response(res)

    def get_estado_pdf(self, clave_estado: str, titulo: Optional[str] = None, subtitulo: Optional[str] = None, logo_url: Optional[str] = None) -> bytes:
        """Descarga el reporte ejecutivo PDF de un Estado en formato binario."""
        params = {}
        if titulo: params["titulo"] = titulo
        if subtitulo: params["subtitulo"] = subtitulo
        if logo_url: params["logo_url"] = logo_url

        with self._get_client() as client:
            res = client.get(f"/api/v1/estados/{clave_estado}/pdf", params=params)
            if res.is_success:
                return res.content
            self._handle_response(res)

    def get_stats(self) -> Dict[str, Any]:
        """Retorna las estadísticas globales del catálogo SEPOMEX."""
        with self._get_client() as client:
            res = client.get("/api/v1/stats")
            return self._handle_response(res)
