"""Geometry and distance calculation toolkit for Mini Agent G4"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from math import radians, cos, sin, asin, sqrt, atan2, degrees
from agno.tools import tool


@dataclass
class Point:
    """Represents a point in 2D or 3D space."""
    x: float
    y: float
    z: Optional[float] = None

    def __post_init__(self):
        if self.z is None:
            self.z = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "z": self.z}


def parse_point(point_str: str) -> Point:
    """Parse a point string like 'x,y' or 'x,y,z' into a Point object."""
    parts = point_str.strip().split(",")
    if len(parts) < 2:
        raise ValueError(f"Invalid point format: {point_str}. Expected 'x,y' or 'x,y,z'")
    x = float(parts[0].strip())
    y = float(parts[1].strip())
    z = float(parts[2].strip()) if len(parts) > 2 else None
    return Point(x=x, y=y, z=z)


def parse_distance_unit(unit: str) -> str:
    """Normalize distance unit."""
    unit = unit.lower().strip()
    valid_units = {
        "km": "km", "kilometers": "km", "kilometres": "km",
        "m": "m", "meters": "m", "metres": "m",
        "mi": "mi", "miles": "mi",
        "ft": "ft", "feet": "ft",
        "nm": "nm", "nmi": "nm", "nautical": "nm",
        "yd": "yd", "yards": "yd",
    }
    return valid_units.get(unit, "m")


class GeometryToolkit:
    """Toolkit for geometry calculations and distance computations."""

    @tool
    def calculate_distance(
        self,
        point1: str,
        point2: str,
        unit: str = "m"
    ) -> str:
        """Calculate the Euclidean distance between two points in 2D or 3D space.

        Args:
            point1: First point in format 'x,y' or 'x,y,z' (e.g., '10,20' or '10,20,5')
            point2: Second point in format 'x,y' or 'x,y,z' (e.g., '30,40' or '30,40,15')
            unit: Unit for distance - 'm' (meters), 'km' (kilometers), 'mi' (miles), 'ft' (feet), 'nm' (nautical miles), 'yd' (yards)

        Returns:
            Distance between the two points in the specified unit.
        """
        p1 = parse_point(point1)
        p2 = parse_point(point2)

        dx = p2.x - p1.x
        dy = p2.y - p1.y
        dz = p2.z - p1.z

        distance_squared = dx**2 + dy**2 + dz**2
        distance = sqrt(distance_squared)

        unit = parse_distance_unit(unit)

        if unit == "km":
            result = distance / 1000
        elif unit == "mi":
            result = distance * 0.000621371
        elif unit == "ft":
            result = distance * 3.28084
        elif unit == "nm":
            result = distance * 0.000539957
        elif unit == "yd":
            result = distance * 1.09361
        else:
            result = distance

        return f"Distance: {result:.4f} {unit}"

    @tool
    def calculate_distance_geo(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
        unit: str = "km"
    ) -> str:
        """Calculate the great-circle distance between two geographic coordinates using the Haversine formula.

        Args:
            lat1: Latitude of first point in degrees (-90 to 90)
            lon1: Longitude of first point in degrees (-180 to 180)
            lat2: Latitude of second point in degrees (-90 to 90)
            lon2: Longitude of second point in degrees (-180 to 180)
            unit: Unit for distance - 'km' (kilometers), 'm' (meters), 'mi' (miles), 'nm' (nautical miles)

        Returns:
            Distance between the two geographic points in the specified unit.
        """
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)

        a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))

        earth_radius = {
            "km": 6371.0,
            "m": 6371000.0,
            "mi": 3958.8,
            "nm": 3440.65,
        }

        radius = earth_radius.get(unit, 6371.0)
        distance = radius * c

        return f"Geographic distance: {distance:.4f} {unit}"

    @tool
    def calculate_bearing(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> str:
        """Calculate the initial bearing (forward azimuth) from point1 to point2.

        Args:
            lat1: Latitude of first point in degrees
            lon1: Longitude of first point in degrees
            lat2: Latitude of second point in degrees
            lon2: Longitude of second point in degrees

        Returns:
            Bearing in degrees (0-360), where 0=North, 90=East, 180=South, 270=West
        """
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        dlon = radians(lon2 - lon1)

        x = sin(dlon) * cos(lat2_rad)
        y = cos(lat1_rad) * sin(lat2_rad) - sin(lat1_rad) * cos(lat2_rad) * cos(dlon)

        bearing = atan2(x, y)
        bearing_degrees = degrees(bearing)

        compass = (bearing_degrees + 360) % 360

        direction = ""
        if 0 <= compass < 22.5 or 337.5 <= compass <= 360:
            direction = "North"
        elif 22.5 <= compass < 67.5:
            direction = "Northeast"
        elif 67.5 <= compass < 112.5:
            direction = "East"
        elif 112.5 <= compass < 157.5:
            direction = "Southeast"
        elif 157.5 <= compass < 202.5:
            direction = "South"
        elif 202.5 <= compass < 247.5:
            direction = "Southwest"
        elif 247.5 <= compass < 292.5:
            direction = "West"
        elif 292.5 <= compass < 337.5:
            direction = "Northwest"

        return f"Bearing: {compass:.2f}° ({direction})"

    @tool
    def check_proximity(
        self,
        point1: str,
        point2: str,
        threshold: float,
        unit: str = "m"
    ) -> str:
        """Check if two points are within a specified threshold distance of each other.

        Args:
            point1: First point in format 'x,y' or 'x,y,z'
            point2: Second point in format 'x,y' or 'x,y,z'
            threshold: Distance threshold value
            unit: Unit for threshold - 'm' (meters), 'km' (kilometers), 'mi' (miles), 'ft' (feet)

        Returns:
            Alert message if points are within threshold, otherwise confirmation they're apart
        """
        p1 = parse_point(point1)
        p2 = parse_point(point2)

        dx = p2.x - p1.x
        dy = p2.y - p1.y
        dz = p2.z - p1.z
        distance = sqrt(dx**2 + dy**2 + dz**2)

        unit = parse_distance_unit(unit)

        if unit == "km":
            distance_display = distance / 1000
            threshold_display = threshold
        elif unit == "mi":
            distance_display = distance * 0.000621371
            threshold_display = threshold
        elif unit == "ft":
            distance_display = distance * 3.28084
            threshold_display = threshold
        else:
            distance_display = distance
            threshold_display = threshold

        if distance_display <= threshold_display:
            return f"ALERT: Points are within threshold! Distance: {distance_display:.4f} {unit} (threshold: {threshold_display:.4f} {unit})"
        else:
            return f"OK: Points are apart. Distance: {distance_display:.4f} {unit} (threshold: {threshold_display:.4f} {unit})"

    @tool
    def calculate_midpoint(
        self,
        point1: str,
        point2: str
    ) -> str:
        """Calculate the midpoint between two points.

        Args:
            point1: First point in format 'x,y' or 'x,y,z'
            point2: Second point in format 'x,y' or 'x,y,z'

        Returns:
            Midpoint coordinates
        """
        p1 = parse_point(point1)
        p2 = parse_point(point2)

        mid_x = (p1.x + p2.x) / 2
        mid_y = (p1.y + p2.y) / 2
        mid_z = (p1.z + p2.z) / 2

        if mid_z == 0:
            return f"Midpoint: ({mid_x:.4f}, {mid_y:.4f})"
        else:
            return f"Midpoint: ({mid_x:.4f}, {mid_y:.4f}, {mid_z:.4f})"

    @tool
    def calculate_velocity(
        self,
        point1: str,
        point2: str,
        time1: float,
        time2: float,
        unit: str = "m/s"
    ) -> str:
        """Calculate velocity between two points over time.

        Args:
            point1: Start point in format 'x,y' or 'x,y,z'
            point2: End point in format 'x,y' or 'x,y,z'
            time1: Start time in seconds
            time2: End time in seconds
            unit: Speed unit - 'm/s', 'km/h', 'mph', 'knots'

        Returns:
            Velocity (speed and direction if applicable)
        """
        p1 = parse_point(point1)
        p2 = parse_point(point2)

        dx = p2.x - p1.x
        dy = p2.y - p1.y
        dz = p2.z - p1.z

        distance = sqrt(dx**2 + dy**2 + dz**2)

        dt = time2 - time1
        if dt <= 0:
            return "Error: Time delta must be positive"

        speed = distance / dt

        if unit == "km/h":
            speed_display = speed * 3.6
        elif unit == "mph":
            speed_display = speed * 2.23694
        elif unit == "knots":
            speed_display = speed * 1.94384
        else:
            speed_display = speed
            unit = "m/s"

        bearing = degrees(atan2(dx, dy)) % 360

        return f"Velocity: {speed_display:.4f} {unit} (bearing: {bearing:.2f}°)"