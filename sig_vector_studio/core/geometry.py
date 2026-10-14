"""
Spatial geometric algorithms: Point-in-polygon, Area, Centroid, BBox, and WKT formatting.
"""
import math
from typing import List, Tuple, Dict, Any, Optional

def point_in_polygon(x: float, y: float, polygon_coords: List[List[float]]) -> bool:
    """
    Ray casting algorithm to test if point (x, y) is inside polygon_coords.
    polygon_coords: [[lon1, lat1], [lon2, lat2], ...]
    """
    n = len(polygon_coords)
    inside = False
    p1x, p1y = polygon_coords[0][0], polygon_coords[0][1]
    for i in range(n + 1):
        p2x, p2y = polygon_coords[i % n][0], polygon_coords[i % n][1]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def polygon_centroid(coords: List[List[float]]) -> Tuple[float, float]:
    """Calculate centroid of a polygon [lon, lat]."""
    if not coords:
        return (0.0, 0.0)
    # Ensure closed ring
    ring = coords[:]
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    
    signed_area = 0.0
    cx = 0.0
    cy = 0.0
    for i in range(len(ring) - 1):
        x0, y0 = ring[i][0], ring[i][1]
        x1, y1 = ring[i + 1][0], ring[i + 1][1]
        a = x0 * y1 - x1 * y0
        signed_area += a
        cx += (x0 + x1) * a
        cy += (y0 + y1) * a
    
    signed_area *= 0.5
    if abs(signed_area) < 1e-12:
        # Fallback to arithmetic mean of points
        mean_x = sum(c[0] for c in coords) / len(coords)
        mean_y = sum(c[1] for c in coords) / len(coords)
        return (mean_x, mean_y)
    
    cx /= (6.0 * signed_area)
    cy /= (6.0 * signed_area)
    return (cx, cy)

def polygon_area_m2(coords: List[List[float]]) -> float:
    """
    Approximate polygon area in square meters using spherical coordinate projection.
    coords: [[lon, lat], ...] in EPSG:4326.
    """
    if len(coords) < 3:
        return 0.0
    # Mean latitude to meter scale conversion
    mean_lat = sum(c[1] for c in coords) / len(coords)
    lat_rad = math.radians(mean_lat)
    # Earth radius ~ 6378137m
    meters_per_deg_lat = 111132.954
    meters_per_deg_lon = 111412.84 * math.cos(lat_rad)

    # Shoelace formula in projected meters
    area = 0.0
    n = len(coords)
    for i in range(n):
        j = (i + 1) % n
        x_i = coords[i][0] * meters_per_deg_lon
        y_i = coords[i][1] * meters_per_deg_lat
        x_j = coords[j][0] * meters_per_deg_lon
        y_j = coords[j][1] * meters_per_deg_lat
        area += (x_i * y_j - x_j * y_i)
    return abs(area) * 0.5

def get_geometry_bbox(geom_type: str, coordinates: Any) -> Tuple[float, float, float, float]:
    """
    Returns (min_lon, min_lat, max_lon, max_lat)
    """
    if geom_type == "Point":
        return (coordinates[0], coordinates[1], coordinates[0], coordinates[1])
    
    lons, lats = [], []
    if geom_type == "LineString":
        for pt in coordinates:
            lons.append(pt[0])
            lats.append(pt[1])
    elif geom_type == "Polygon":
        for ring in coordinates:
            for pt in ring:
                lons.append(pt[0])
                lats.append(pt[1])
    elif geom_type == "MultiPolygon":
        for poly in coordinates:
            for ring in poly:
                for pt in ring:
                    lons.append(pt[0])
                    lats.append(pt[1])
    
    if not lons:
        return (0.0, 0.0, 0.0, 0.0)
    return (min(lons), min(lats), max(lons), max(lats))

def bboxes_intersect(b1: Tuple[float, float, float, float], b2: Tuple[float, float, float, float]) -> bool:
    """Returns True if bbox1 intersects bbox2."""
    minx1, miny1, maxx1, maxy1 = b1
    minx2, miny2, maxx2, maxy2 = b2
    return not (maxx1 < minx2 or minx1 > maxx2 or maxy1 < miny2 or miny1 > maxy2)

def to_wkt(geom_type: str, coordinates: Any) -> str:
    """
    Convert GeoJSON geometry type & coordinates to SQL Server OGC Well-Known Text (WKT).
    SRID is typically 4326 (Long Lat).
    """
    if geom_type == "Point":
        return f"POINT({coordinates[0]:.7f} {coordinates[1]:.7f})"
    
    if geom_type == "LineString":
        pts = ", ".join(f"{p[0]:.7f} {p[1]:.7f}" for p in coordinates)
        return f"LINESTRING({pts})"
    
    if geom_type == "Polygon":
        rings = []
        for ring in coordinates:
            # SQL Server requires outer ring closed
            if ring[0] != ring[-1]:
                ring = ring + [ring[0]]
            pts = ", ".join(f"{p[0]:.7f} {p[1]:.7f}" for p in ring)
            rings.append(f"({pts})")
        return f"POLYGON({', '.join(rings)})"
    
    if geom_type == "MultiPolygon":
        polys = []
        for poly in coordinates:
            rings = []
            for ring in poly:
                if ring[0] != ring[-1]:
                    ring = ring + [ring[0]]
                pts = ", ".join(f"{p[0]:.7f} {p[1]:.7f}" for p in ring)
                rings.append(f"({pts})")
            polys.append(f"({', '.join(rings)})")
        return f"MULTIPOLYGON({', '.join(polys)})"
    
    return ""

def from_wkt(wkt_str: str) -> Tuple[str, Any]:
    """
    Parses Point, LineString, Polygon, MultiPolygon WKT string into (geom_type, coordinates).
    Compatible with SQL Server OGC / Geography STAsText() outputs.
    """
    import re
    if not wkt_str:
        return "", None
    w = wkt_str.strip()
    u = w.upper()
    if u.startswith("POINT"):
        c = w[w.find("(") + 1:w.rfind(")")].strip().split()
        if len(c) >= 2:
            return "Point", [float(c[0]), float(c[1])]
    elif u.startswith("LINESTRING"):
        c = w[w.find("(") + 1:w.rfind(")")].strip()
        pts = []
        for pair in c.split(","):
            parts = pair.strip().split()
            if len(parts) >= 2:
                pts.append([float(parts[0]), float(parts[1])])
        return "LineString", pts
    elif u.startswith("POLYGON"):
        c = w[w.find("(") + 1:w.rfind(")")].strip()
        rings = []
        for r in re.findall(r"\(([^()]+)\)", c):
            ring = []
            for pair in r.split(","):
                parts = pair.strip().split()
                if len(parts) >= 2:
                    ring.append([float(parts[0]), float(parts[1])])
            if ring:
                rings.append(ring)
        return "Polygon", rings
    elif u.startswith("MULTIPOLYGON"):
        polys = []
        raw_polys = re.findall(r"\(\s*(\([^()]+\)(?:\s*,\s*\([^()]+\))*)\s*\)", w)
        for rp in raw_polys:
            rings = []
            for rr in re.findall(r"\(([^()]+)\)", rp):
                ring = []
                for pair in rr.split(","):
                    parts = pair.strip().split()
                    if len(parts) >= 2:
                        ring.append([float(parts[0]), float(parts[1])])
                if ring:
                    rings.append(ring)
            if rings:
                polys.append(rings)
        return "MultiPolygon", polys
    return "", None

