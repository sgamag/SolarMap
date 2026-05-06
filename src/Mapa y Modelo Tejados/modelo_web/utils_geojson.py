import json
import math
import cv2
import numpy as np


def pixel_to_geo(x, y, width, height, metadata):
    top_left = metadata["bbox"]["top_left"]
    top_right = metadata["bbox"]["top_right"]
    bottom_left = metadata["bbox"]["bottom_left"]

    lat_max = top_left["lat"]
    lat_min = bottom_left["lat"]

    lon_min = top_left.get("lon", top_left.get("lng"))
    lon_max = top_right.get("lon", top_right.get("lng"))

    lon = lon_min + (x / width) * (lon_max - lon_min)
    lat = lat_max - (y / height) * (lat_max - lat_min)

    return [float(lon), float(lat)]


def calcular_orientacion(contorno):
    puntos = contorno.reshape(-1, 2).astype(np.float32)

    if len(puntos) < 2:
        return None, "No calculable"

    _, eigenvectors = cv2.PCACompute(puntos, mean=None)
    vx, vy = eigenvectors[0]

    angulo = math.degrees(math.atan2(vy, vx))

    if angulo < 0:
        angulo += 180

    if angulo >= 180:
        angulo -= 180

    if 0 <= angulo < 22.5 or 157.5 <= angulo <= 180:
        orientacion = "Este-Oeste"
    elif 22.5 <= angulo < 67.5:
        orientacion = "Noroeste-Sureste"
    elif 67.5 <= angulo < 112.5:
        orientacion = "Norte-Sur"
    else:
        orientacion = "Noreste-Suroeste"

    return float(round(angulo, 2)), orientacion


def mask_to_geojson(mask_np, metadata, threshold=0.70, area_minima_px=150):
    mask_np = np.squeeze(mask_np)
    mask_np = (mask_np > 0).astype(np.uint8)

    kernel_open = np.ones((3, 3), np.uint8)
    kernel_close = np.ones((5, 5), np.uint8)

    mask_clean = cv2.morphologyEx(mask_np, cv2.MORPH_OPEN, kernel_open)
    mask_clean = cv2.morphologyEx(mask_clean, cv2.MORPH_CLOSE, kernel_close)

    height, width = mask_clean.shape

    area_m2_per_pixel = metadata["meters_per_pixel"]["area_m2_per_pixel"]

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        mask_clean,
        connectivity=8
    )

    features = []

    for label in range(1, num_labels):
        area_px_componente = stats[label, cv2.CC_STAT_AREA]

        if area_px_componente < area_minima_px:
            continue

        component = (labels == label).astype(np.uint8) * 255

        contours, _ = cv2.findContours(
            component,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        for cnt in contours:
            area_px = cv2.contourArea(cnt)

            if area_px < area_minima_px:
                continue

            epsilon = 0.01 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)

            coords = []

            for point in approx:
                x, y = point[0]
                coords.append(pixel_to_geo(x, y, width, height, metadata))

            if len(coords) < 3:
                continue

            if coords[0] != coords[-1]:
                coords.append(coords[0])

            area_m2 = area_px * area_m2_per_pixel
            angulo, orientacion = calcular_orientacion(cnt)

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords]
                },
                "properties": {
                    "id": len(features) + 1,
                    "zoom": metadata.get("zoom"),
                    "threshold": threshold,
                    "area_px": float(round(area_px, 2)),
                    "area_m2": float(round(area_m2, 2)),
                    "orientation_angle_degrees": angulo,
                    "orientation_label": orientacion
                }
            }

            features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }


def cargar_metadata(metadata_path):
    with open(metadata_path, "r", encoding="utf-8") as f:
        return json.load(f)