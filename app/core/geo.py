import math
from typing import Tuple

# Constante del radio promedio de la Tierra en kilómetros
EARTH_RADIUS_KM = 6371.0088


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula la distancia ortodrómica (distancia en gran círculo) entre dos puntos geográficos
    en la Tierra utilizando la Fórmula de Haversine. Retorna la distancia en kilómetros (km).
    """
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    
    r_lat1 = math.radians(lat1)
    r_lat2 = math.radians(lat2)
    
    a = (math.sin(d_lat / 2) ** 2) + (math.cos(r_lat1) * math.cos(r_lat2) * (math.sin(d_lon / 2) ** 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return round(EARTH_RADIUS_KM * c, 3)


def calculate_bounding_box(lat: float, lon: float, distance_km: float) -> Tuple[float, float, float, float]:
    """
    Calcula una Caja Delimitadora Geográfica (Bounding Box) alrededor de un punto (lat, lon)
    para un radio determinado en kilómetros.
    Retorna: (min_lat, max_lat, min_lon, max_lon)
    """
    lat_delta = distance_km / 111.0  # ~111 km por grado de latitud
    # Ajuste por convergencia de meridianos según la latitud
    lon_delta = distance_km / (111.0 * math.cos(math.radians(lat)))
    
    min_lat = round(lat - lat_delta, 6)
    max_lat = round(lat + lat_delta, 6)
    min_lon = round(lon - abs(lon_delta), 6)
    max_lon = round(lon + abs(lon_delta), 6)
    
    return (min_lat, max_lat, min_lon, max_lon)
