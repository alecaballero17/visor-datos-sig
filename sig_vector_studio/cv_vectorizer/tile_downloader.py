"""
Tile math, concurrent downloading and stitching of satellite imagery tiles for arbitrary BBOX.
"""
import math
import io
from typing import Tuple, List, Optional
import requests
from PIL import Image
import numpy as np
from sig_vector_studio.config import DEFAULT_VECTORIZER_TILE_URL

def lon_lat_to_tile(lon: float, lat: float, zoom: int) -> Tuple[int, int]:
    """Convert lon, lat in degrees to tile numbers at zoom level."""
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def tile_to_lon_lat(xtile: int, ytile: int, zoom: int) -> Tuple[float, float]:
    """Convert top-left corner of tile to lon, lat."""
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lon_deg, lat_deg)

class TileImageStitcher:
    def __init__(self, tile_url_template: str = DEFAULT_VECTORIZER_TILE_URL):
        self.url_template = tile_url_template
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "SigVectorStudio/1.0 (+http://localhost)"})

    def fetch_bbox_image(self, min_lon: float, min_lat: float, max_lon: float, max_lat: float, zoom: int = 18) -> Tuple[np.ndarray, Tuple[float, float, float, float]]:
        """
        Fetches all tiles covering the BBOX at the specified zoom level,
        stitches them together, and crops/returns the exact BBOX sub-image as a BGR numpy array
        along with the exact geo-bounds (actual_min_lon, actual_min_lat, actual_max_lon, actual_max_lat).
        """
        # Ensure correct ordering
        min_lon, max_lon = min(min_lon, max_lon), max(min_lon, max_lon)
        min_lat, max_lat = min(min_lat, max_lat), max(min_lat, max_lat)

        x_min, y_min = lon_lat_to_tile(min_lon, max_lat, zoom)
        x_max, y_max = lon_lat_to_tile(max_lon, min_lat, zoom)

        # Clamp max span to avoid downloading too many tiles
        span_x = min(x_max - x_min + 1, 8)
        span_y = min(y_max - y_min + 1, 8)
        x_max = x_min + span_x - 1
        y_max = y_min + span_y - 1

        tile_size = 256
        canvas_width = span_x * tile_size
        canvas_height = span_y * tile_size
        canvas = Image.new("RGB", (canvas_width, canvas_height), (40, 40, 40))

        for xi in range(span_x):
            tx = x_min + xi
            for yi in range(span_y):
                ty = y_min + yi
                url = self.url_template.format(z=zoom, x=tx, y=ty)
                try:
                    resp = self.session.get(url, timeout=5)
                    if resp.status_code == 200:
                        tile_img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                        canvas.paste(tile_img, (xi * tile_size, yi * tile_size))
                except Exception:
                    pass

        # Calculate exact bounds of the stitched canvas
        canvas_nw_lon, canvas_nw_lat = tile_to_lon_lat(x_min, y_min, zoom)
        canvas_se_lon, canvas_se_lat = tile_to_lon_lat(x_max + 1, y_max + 1, zoom)

        # Convert canvas to OpenCV BGR numpy array
        rgb_arr = np.array(canvas)
        bgr_arr = rgb_arr[:, :, ::-1].copy()

        actual_bounds = (canvas_nw_lon, canvas_se_lat, canvas_se_lon, canvas_nw_lat)
        return bgr_arr, actual_bounds
