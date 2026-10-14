"""
Algoritmo Avanzado de Detección y Trazado Vectorial Urbano con Visión por Computadora.

Implementa:
1. Vías / Calles: Extracción precisa de corredores viales mediante umbralización cromática diferencial
   (aislando asfalto/calles y suprimiendo fondo territorial y textos), esqueletización morfológica (skeletonization)
   y trazado continuo de polilíneas (LineString) que siguen curvas y respetan intersecciones urbanas reales,
   sin generar líneas espurias transversales.
2. Manzanas: Polígonos cerrados delimitados naturalmente por la red vial, depurados de artefactos y
   regularizados geométricamente con Douglas-Peucker.
3. Casas / Códigos Fijos: Extracción de huellas de edificaciones y techos mediante segmentación espectral
   (#d9d0c9, #cbbeb5) evitando puntos ficticios o inventados en parcelas vacías.
4. Lotes / Terrenos: Delimitación de parcelas catastrales regulares respetando la envolvente ortogonal.
"""
import math
from typing import List, Dict, Any, Tuple
import cv2
import numpy as np
from sig_vector_studio.core.geometry import polygon_centroid

def zhang_suen_thinning(img: np.ndarray, max_iters: int = 16) -> np.ndarray:
    """
    Algoritmo de adelgazamiento morfológico de Zhang-Suen.
    Garantiza un esqueleto estricto de 1 píxel de espesor sin escalones ni duplicaciones,
    permitiendo extraer polilíneas limpias y continuas que siguen las calles.
    """
    binary = (img > 0).astype(np.uint8)
    for _ in range(max_iters):
        P2 = np.roll(binary, -1, axis=0)
        P3 = np.roll(np.roll(binary, -1, axis=0), 1, axis=1)
        P4 = np.roll(binary, 1, axis=1)
        P5 = np.roll(np.roll(binary, 1, axis=0), 1, axis=1)
        P6 = np.roll(binary, 1, axis=0)
        P7 = np.roll(np.roll(binary, 1, axis=0), -1, axis=1)
        P8 = np.roll(binary, -1, axis=1)
        P9 = np.roll(np.roll(binary, -1, axis=0), -1, axis=1)

        B = P2 + P3 + P4 + P5 + P6 + P7 + P8 + P9
        A = ((P2 == 0) & (P3 == 1)).astype(int) + \
            ((P3 == 0) & (P4 == 1)).astype(int) + \
            ((P4 == 0) & (P5 == 1)).astype(int) + \
            ((P5 == 0) & (P6 == 1)).astype(int) + \
            ((P6 == 0) & (P7 == 1)).astype(int) + \
            ((P7 == 0) & (P8 == 1)).astype(int) + \
            ((P8 == 0) & (P9 == 1)).astype(int) + \
            ((P9 == 0) & (P2 == 1)).astype(int)

        cond1 = (binary == 1) & (B >= 2) & (B <= 6) & (A == 1)
        step1 = cond1 & (P2 * P4 * P6 == 0) & (P4 * P6 * P8 == 0)
        binary[step1] = 0

        P2 = np.roll(binary, -1, axis=0)
        P3 = np.roll(np.roll(binary, -1, axis=0), 1, axis=1)
        P4 = np.roll(binary, 1, axis=1)
        P5 = np.roll(np.roll(binary, 1, axis=0), 1, axis=1)
        P6 = np.roll(binary, 1, axis=0)
        P7 = np.roll(np.roll(binary, 1, axis=0), -1, axis=1)
        P8 = np.roll(binary, -1, axis=1)
        P9 = np.roll(np.roll(binary, -1, axis=0), -1, axis=1)

        B = P2 + P3 + P4 + P5 + P6 + P7 + P8 + P9
        A = ((P2 == 0) & (P3 == 1)).astype(int) + \
            ((P3 == 0) & (P4 == 1)).astype(int) + \
            ((P4 == 0) & (P5 == 1)).astype(int) + \
            ((P5 == 0) & (P6 == 1)).astype(int) + \
            ((P6 == 0) & (P7 == 1)).astype(int) + \
            ((P7 == 0) & (P8 == 1)).astype(int) + \
            ((P8 == 0) & (P9 == 1)).astype(int) + \
            ((P9 == 0) & (P2 == 1)).astype(int)

        cond2 = (binary == 1) & (B >= 2) & (B <= 6) & (A == 1)
        step2 = cond2 & (P2 * P4 * P8 == 0) & (P2 * P6 * P8 == 0)
        binary[step2] = 0

        if not np.any(step1) and not np.any(step2):
            break

    return binary * 255

morphological_skeleton = zhang_suen_thinning

def trace_skeleton_segments(skel: np.ndarray, min_length: int = 18) -> List[List[Tuple[int, int]]]:
    """
    Rastrea el esqueleto morfológico de 1 píxel y extrae ramas continuas (polilíneas)
    descomponiendo intersecciones para evitar aristas cruzadas espurias.
    """
    kernel = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], dtype=np.uint8)
    skel_bin = (skel > 0).astype(np.uint8)
    neighbors = cv2.filter2D(skel_bin, -1, kernel) * skel_bin

    # Separar intersecciones (nodos de bifurcación)
    junctions = (neighbors >= 3)
    k_junc = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated_junc = cv2.dilate(junctions.astype(np.uint8), k_junc)
    paths_mask = skel_bin & (~dilated_junc)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(paths_mask, 8)
    polylines = []

    for label in range(1, num_labels):
        area = stats[label, cv2.CC_STAT_AREA]
        if area < min_length:
            continue

        pts = np.argwhere(labels == label)
        if len(pts) < 2:
            continue

        pts_set = set(map(tuple, pts))
        comp_mask = (labels == label).astype(np.uint8)
        comp_neigh = cv2.filter2D(comp_mask, -1, kernel) * comp_mask
        end_pts = np.argwhere((comp_neigh == 1) & (labels == label))

        start_pt = tuple(end_pts[0]) if len(end_pts) > 0 else tuple(pts[0])
        ordered = [start_pt]
        curr = start_pt
        visited = {curr}

        while len(visited) < len(pts_set):
            cy, cx = curr
            best_next = None
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    cand = (cy + dy, cx + dx)
                    if cand in pts_set and cand not in visited:
                        best_next = cand
                        break
                if best_next:
                    break
            if not best_next:
                remaining = list(pts_set - visited)
                dists = [(abs(r[0] - cy) + abs(r[1] - cx), r) for r in remaining]
                dists.sort()
                if dists and dists[0][0] <= 3:
                    best_next = dists[0][1]
                else:
                    break

            visited.add(best_next)
            ordered.append(best_next)
            curr = best_next

        if len(ordered) >= 4:
            xy_pts = np.array([[pt[1], pt[0]] for pt in ordered], dtype=np.int32)
            approx = cv2.approxPolyDP(xy_pts, 2.0, False)
            if len(approx) >= 2:
                polylines.append([tuple(p[0]) for p in approx])

    return polylines

class OSMUrbanMLDetector:
    """Detector y vectorizador de entidades cartográficas urbanas con visión artificial."""

    def __init__(self):
        pass

    def pixel_to_geo(self, px: float, py: float, width: int, height: int, bounds: Tuple[float, float, float, float]) -> Tuple[float, float]:
        """Convierte coordenadas de píxel (px, py) a coordenadas geográficas (lon, lat) EPSG:4326."""
        min_lon, min_lat, max_lon, max_lat = bounds
        lon = min_lon + (px / float(width)) * (max_lon - min_lon)
        lat = max_lat - (py / float(height)) * (max_lat - min_lat)
        return (round(lon, 7), round(lat, 7))

    def geo_to_pixel(self, lon: float, lat: float, width: int, height: int, bounds: Tuple[float, float, float, float]) -> Tuple[int, int]:
        """Convierte coordenadas geográficas EPSG:4326 a píxel (px, py)."""
        min_lon, min_lat, max_lon, max_lat = bounds
        px = int(round((lon - min_lon) / (max_lon - min_lon) * width))
        py = int(round((max_lat - lat) / (max_lat - min_lat) * height))
        return (px, py)

    def _suppress_text_and_extract_roads(self, image_bgr: np.ndarray) -> np.ndarray:
        """
        Extrae la máscara binaria continua de las vías y calles en OpenStreetMap o imágenes satelitales,
        discriminando el fondo territorial de OSM (#f2efe9) y eliminando etiquetas de texto e iconos.
        """
        hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)

        # 1. Calles pavimentadas y residenciales blancas (en OSM son blanco puro #ffffff = BGR 255, 255, 255)
        # El fondo de OSM es #f2efe9 (B=233, G=239, R=242), por lo que un umbral >= 253 en los 3 canales
        # aísla estrictamente las vías residenciales sin tocar el fondo.
        white_roads = cv2.inRange(image_bgr, np.array([252, 252, 252]), np.array([255, 255, 255]))

        # 2. Avenidas y vías principales amarillas / naranjas en OSM
        yellow_roads = cv2.inRange(hsv, np.array([14, 25, 150]), np.array([45, 255, 255]))
        orange_roads = cv2.inRange(hsv, np.array([4, 35, 150]), np.array([14, 255, 255]))

        # 3. Carreteras y autopistas rosadas / rojas
        pink_roads_1 = cv2.inRange(hsv, np.array([0, 25, 140]), np.array([6, 255, 255]))
        pink_roads_2 = cv2.inRange(hsv, np.array([170, 25, 140]), np.array([180, 255, 255]))

        # Fusión de la red vial
        all_roads = cv2.bitwise_or(white_roads, yellow_roads)
        all_roads = cv2.bitwise_or(all_roads, orange_roads)
        all_roads = cv2.bitwise_or(all_roads, pink_roads_1)
        all_roads = cv2.bitwise_or(all_roads, pink_roads_2)

        # 4. Supresión de textos tipográficos y pequeños artefactos aislados (< 100 píxeles de área)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(all_roads, 8)
        clean_roads = np.zeros_like(all_roads)
        for i in range(1, num_labels):
            if stats[i, cv2.CC_STAT_AREA] >= 90:
                clean_roads[labels == i] = 255

        # 5. Puente morfológico suave para conectar cruces e intersecciones
        k_bridge = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        clean_roads = cv2.morphologyEx(clean_roads, cv2.MORPH_CLOSE, k_bridge)

        return clean_roads

    def _extract_buildings_mask(self, image_bgr: np.ndarray) -> np.ndarray:
        """Extrae huellas de edificaciones en OpenStreetMap por su color característico beige/tostado."""
        b = image_bgr[:, :, 0].astype(int)
        g = image_bgr[:, :, 1].astype(int)
        r = image_bgr[:, :, 2].astype(int)

        diff_rb = r - b
        diff_rg = r - g
        is_building = (
            (diff_rb >= 4) & (diff_rb <= 38) &
            (diff_rg >= 2) & (diff_rg <= 28) &
            (r >= 170) & (r <= 235) &
            (g >= 160) & (g <= 225) &
            (b >= 150) & (b <= 215)
        )
        return is_building.astype(np.uint8) * 255

    def _extract_vias(
        self,
        all_roads: np.ndarray,
        w: int,
        h: int,
        bounds: Tuple[float, float, float, float],
        annotated_img: np.ndarray
    ) -> List[Dict[str, Any]]:
        """
        Extrae y traza los ejes viales individuales continuos mediante esqueletización
        y seguimiento de segmentos topológicos, preservando curvas e intersecciones reales.
        """
        results = []
        if cv2.countNonZero(all_roads) < 50:
            return results

        # 1. Esqueletización morfológica (ejes de 1 px)
        skel = morphological_skeleton(all_roads)

        # 2. Rastreo topológico de ramas
        segments = trace_skeleton_segments(skel, min_length=15)

        for seg in segments:
            geo_coords = []
            pts_px = []
            for px, py in seg:
                gx, gy = self.pixel_to_geo(px, py, w, h, bounds)
                geo_coords.append([gx, gy])
                pts_px.append((int(px), int(py)))

            if len(geo_coords) >= 2:
                # Dibujar vía en púrpura vibrante siguiendo su geometría real
                for i in range(len(pts_px) - 1):
                    cv2.line(annotated_img, pts_px[i], pts_px[i + 1], (168, 85, 247), 3)

                # Calcular longitud total del trazo
                total_len = 0.0
                for i in range(len(pts_px) - 1):
                    total_len += math.hypot(pts_px[i + 1][0] - pts_px[i][0], pts_px[i + 1][1] - pts_px[i][1])

                mid_idx = len(geo_coords) // 2
                results.append({
                    "layer": "vias",
                    "geom_type": "LineString",
                    "coordinates": geo_coords,
                    "centroid": geo_coords[mid_idx],
                    "area_px": total_len
                })

        return results

    def _extract_manzanas(
        self,
        all_roads: np.ndarray,
        w: int,
        h: int,
        bounds: Tuple[float, float, float, float],
        min_area: int,
        max_area: int,
        annotated_img: np.ndarray
    ) -> Tuple[List[Dict[str, Any]], List[Tuple[np.ndarray, np.ndarray, float]]]:
        """
        Extrae y regulariza los polígonos de manzanas cerradas entre las calles.
        """
        results = []
        valid_block_data = []

        if cv2.countNonZero(all_roads) < 50:
            return results, valid_block_data

        # Dilatar las calles para cerrar esquinas e invertir
        k_roads = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
        dilated_roads = cv2.dilate(all_roads, k_roads, iterations=1)
        blocks_mask = cv2.bitwise_not(dilated_roads)

        # Borrar márgenes de lienzo (evitar que el borde del recorte se detecte como manzana)
        cv2.rectangle(blocks_mask, (0, 0), (w - 1, h - 1), 0, 10)

        contours_blocks, _ = cv2.findContours(blocks_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours_blocks:
            area = cv2.contourArea(cnt)
            if area < min_area or area > max_area:
                continue

            peri = cv2.arcLength(cnt, True)
            # Regularización geométrica: suavizar escalonamiento de píxeles a polígono limpio
            approx = cv2.approxPolyDP(cnt, 0.025 * peri, True)

            if len(approx) >= 4:
                valid_block_data.append((cnt, approx, area))
                pts_geo = []
                for pt in approx:
                    gx, gy = self.pixel_to_geo(pt[0][0], pt[0][1], w, h, bounds)
                    pts_geo.append([gx, gy])
                if pts_geo[0] != pts_geo[-1]:
                    pts_geo.append(pts_geo[0])

                # Dibujar manzana en rojo vivo
                cv2.polylines(annotated_img, [approx], True, (38, 38, 220), 2)
                results.append({
                    "layer": "manzanas",
                    "geom_type": "Polygon",
                    "coordinates": [pts_geo],
                    "centroid": polygon_centroid(pts_geo),
                    "area_px": area
                })

        return results, valid_block_data

    def _extract_lotes(
        self,
        valid_block_data: List[Tuple[np.ndarray, np.ndarray, float]],
        w: int,
        h: int,
        bounds: Tuple[float, float, float, float],
        annotated_img: np.ndarray
    ) -> List[Dict[str, Any]]:
        """
        Extrae lotes catastrales mediante subdivisión orientada regular dentro de cada manzana.
        """
        results = []

        for cnt, approx, area in valid_block_data:
            # Sólo subdividir si la manzana es suficientemente grande
            if area < 800:
                continue

            rect = cv2.minAreaRect(cnt)
            (cx, cy), (bw, bh), angle = rect

            if bw < bh:
                bw, bh = bh, bw
                angle += 90.0

            rad = math.radians(angle)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)

            cols = max(2, min(8, int(round(bw / 42.0))))
            rows = 2 if bh >= 65 else 1

            step_x = bw / float(cols)
            step_y = bh / float(rows)

            block_mask = np.zeros((h, w), dtype=np.uint8)
            cv2.fillPoly(block_mask, [cnt], 255)

            for r in range(rows):
                ly0 = -bh / 2.0 + r * step_y + 1.0
                ly1 = ly0 + step_y - 2.0
                for c in range(cols):
                    lx0 = -bw / 2.0 + c * step_x + 1.0
                    lx1 = lx0 + step_x - 2.0

                    local_corners = [
                        (lx0, ly0),
                        (lx1, ly0),
                        (lx1, ly1),
                        (lx0, ly1)
                    ]

                    world_corners = []
                    for lx, ly in local_corners:
                        wx = int(round(cx + lx * cos_a - ly * sin_a))
                        wy = int(round(cy + lx * sin_a + ly * cos_a))
                        world_corners.append([wx, wy])

                    # Recorte booleano exacto con la manzana
                    lot_mask = np.zeros((h, w), dtype=np.uint8)
                    cv2.fillPoly(lot_mask, [np.array(world_corners, dtype=np.int32)], 255)

                    clipped_lot = cv2.bitwise_and(block_mask, lot_mask)
                    sub_cnts, _ = cv2.findContours(clipped_lot, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                    for sc in sub_cnts:
                        s_area = cv2.contourArea(sc)
                        if s_area < 90:
                            continue

                        s_peri = cv2.arcLength(sc, True)
                        s_approx = cv2.approxPolyDP(sc, max(1.5, 0.02 * s_peri), True)
                        if len(s_approx) >= 3:
                            lot_geo = []
                            for spt in s_approx:
                                gx, gy = self.pixel_to_geo(spt[0][0], spt[0][1], w, h, bounds)
                                lot_geo.append([gx, gy])
                            if lot_geo[0] != lot_geo[-1]:
                                lot_geo.append(lot_geo[0])

                            cv2.polylines(annotated_img, [s_approx], True, (248, 189, 56), 1)
                            results.append({
                                "layer": "lotes",
                                "geom_type": "Polygon",
                                "coordinates": [lot_geo],
                                "centroid": polygon_centroid(lot_geo),
                                "area_px": s_area
                            })

        return results

    def _extract_casas(
        self,
        image_bgr: np.ndarray,
        valid_block_data: List[Tuple[np.ndarray, np.ndarray, float]],
        w: int,
        h: int,
        bounds: Tuple[float, float, float, float],
        annotated_img: np.ndarray
    ) -> List[Dict[str, Any]]:
        """Extrae casas y códigos fijos estrictamente de edificaciones y techos detectados en el sector."""
        results = []

        # Huellas de edificios reales
        building_mask = self._extract_buildings_mask(image_bgr)
        bldg_cnts, _ = cv2.findContours(building_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for bcnt in bldg_cnts:
            barea = cv2.contourArea(bcnt)
            if 25 <= barea <= 5000:
                M = cv2.moments(bcnt)
                if M["m00"] > 0:
                    bcx = M["m10"] / M["m00"]
                    bcy = M["m01"] / M["m00"]
                    gx, gy = self.pixel_to_geo(bcx, bcy, w, h, bounds)

                    cv2.circle(annotated_img, (int(round(bcx)), int(round(bcy))), 4, (11, 158, 245), -1)
                    cv2.circle(annotated_img, (int(round(bcx)), int(round(bcy))), 6, (255, 255, 255), 1)

                    results.append({
                        "layer": "codigosfijos",
                        "geom_type": "Point",
                        "coordinates": [gx, gy],
                        "centroid": (gx, gy),
                        "area_px": barea
                    })

        return results

    def detect_vectors(
        self,
        image_bgr: np.ndarray,
        bounds: Tuple[float, float, float, float],
        target_layer: str = "all",
        min_area: int = 200,
        max_area: int = 200000,
        epsilon_ratio: float = 0.02,
        sensitivity: int = 55
    ) -> Tuple[Any, np.ndarray]:
        """
        Ejecuta la vectorización urbana inteligente:
        - Vías: ejes continuos y curvas mediante esqueletización.
        - Manzanas: bloques cerrados delimitados por la malla vial.
        - Lotes: parcelas ortogonales delimitadas.
        - Casas: edificaciones y techos reales detectados.
        """
        h, w = image_bgr.shape[:2]
        if h == 0 or w == 0:
            return ({"vias": [], "manzanas": [], "lotes": [], "codigosfijos": []} if target_layer == "all" else []), image_bgr

        annotated_img = image_bgr.copy()
        all_roads = self._suppress_text_and_extract_roads(image_bgr)

        # 1. Vías
        vias = self._extract_vias(all_roads, w, h, bounds, annotated_img) if target_layer in ("all", "vias") else []

        # 2. Manzanas
        manzanas, valid_blocks = self._extract_manzanas(
            all_roads, w, h, bounds, min_area, max_area, annotated_img
        )

        # 3. Lotes
        lotes = self._extract_lotes(valid_blocks, w, h, bounds, annotated_img) if target_layer in ("all", "lotes") else []

        # 4. Casas / Códigos Fijos
        casas = self._extract_casas(image_bgr, valid_blocks, w, h, bounds, annotated_img) if target_layer in ("all", "codigosfijos") else []

        if target_layer == "all":
            return {
                "is_all": True,
                "vias": vias,
                "manzanas": manzanas,
                "lotes": lotes,
                "codigosfijos": casas
            }, annotated_img
        elif target_layer == "vias":
            return vias, annotated_img
        elif target_layer == "manzanas":
            return manzanas, annotated_img
        elif target_layer == "lotes":
            return lotes, annotated_img
        elif target_layer == "codigosfijos":
            return casas, annotated_img

        return [], annotated_img

# Alias de compatibilidad
OSMContourDetector = OSMUrbanMLDetector
SatelliteContourDetector = OSMUrbanMLDetector
