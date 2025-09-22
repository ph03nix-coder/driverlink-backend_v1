import requests
import asyncio
from typing import List, Tuple, Optional
from config import OSRM_BASE_URL

class OSRMClient:
    def __init__(self, base_url: str = OSRM_BASE_URL):
        self.base_url = base_url.rstrip('/')
        
    def _build_coordinates_string(self, coordinates: List[Tuple[float, float]]) -> str:
        """Build coordinate string for OSRM API"""
        return ";".join([f"{lon},{lat}" for lat, lon in coordinates])
    
    def get_distance_and_duration(self, start: Tuple[float, float], end: Tuple[float, float]) -> Optional[dict]:
        """
        Get distance and duration between two points using OSRM
        Returns dict with distance_km and duration_minutes
        """
        try:
            coordinates = self._build_coordinates_string([start, end])
            url = f"{self.base_url}/route/v1/driving/{coordinates}"
            
            params = {
                "overview": "false",
                "steps": "false",
                "geometries": "geojson"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data["code"] != "Ok" or not data["routes"]:
                return None
            
            route = data["routes"][0]
            distance_m = route["distance"]
            duration_s = route["duration"]
            
            return {
                "distance_km": distance_m / 1000,
                "duration_minutes": duration_s / 60,
                "distance_m": distance_m,
                "duration_s": duration_s
            }
            
        except Exception as e:
            print(f"OSRM API error: {e}")
            return None
    
    def get_distances_from_point(self, start: Tuple[float, float], destinations: List[Tuple[float, float]]) -> List[Optional[dict]]:
        """
        Get distances from one point to multiple destinations
        Returns list of distance/duration dicts in same order as destinations
        """
        results = []
        
        for destination in destinations:
            result = self.get_distance_and_duration(start, destination)
            results.append(result)
        
        return results
    
    async def get_distance_and_duration_async(self, start: Tuple[float, float], end: Tuple[float, float]) -> Optional[dict]:
        """Async version of get_distance_and_duration"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_distance_and_duration, start, end)
    
    def calculate_drivers_distances(self, pickup_location: Tuple[float, float], driver_locations: List[Tuple[float, float, int]]) -> List[dict]:
        """
        Calculate distances from pickup location to multiple drivers
        driver_locations: List of (lat, lon, driver_id) tuples
        Returns: List of dicts with driver_id, distance_km, duration_minutes
        """
        results = []
        
        for lat, lon, driver_id in driver_locations:
            driver_location = (lat, lon)
            route_info = self.get_distance_and_duration(pickup_location, driver_location)
            
            if route_info:
                results.append({
                    "driver_id": driver_id,
                    "distance_km": route_info["distance_km"],
                    "duration_minutes": route_info["duration_minutes"]
                })
            else:
                # If OSRM fails, calculate straight-line distance as fallback
                distance_km = self.calculate_haversine_distance(pickup_location, driver_location)
                results.append({
                    "driver_id": driver_id,
                    "distance_km": distance_km,
                    "duration_minutes": distance_km * 2  # Rough estimate: 2 minutes per km in city
                })
        
        return results
    
    @staticmethod
    def calculate_haversine_distance(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
        """
        Calculate the great circle distance between two points on earth
        Returns distance in kilometers
        """
        import math
        
        lat1, lon1 = point1
        lat2, lon2 = point2
        
        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        
        return c * r

# Global OSRM client instance
osrm_client = OSRMClient()