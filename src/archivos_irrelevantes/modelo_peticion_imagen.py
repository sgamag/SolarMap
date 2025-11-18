from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Literal, Tuple

# Tipos aceptados (puedes ampliar)
Collection = Literal["SENTINEL-2"]
ProductType = Literal["S2MSI2A", "S2MSI1C"]

# =========================
# Rangos de tiempo
# =========================
@dataclass
class TimeRange:
    start: date
    end: date

    def iso_bounds(self) -> Tuple[str, str]:
        if self.end < self.start:
            raise ValueError("La fecha final no puede ser anterior a la inicial.")
        iso_start = f"{self.start.isoformat()}T00:00:00.000Z"
        iso_end   = f"{self.end.isoformat()}T23:59:59.999Z"
        return iso_start, iso_end

# =========================
# Área de interés (WKT EPSG:4326)
# =========================
@dataclass
class AOI:
    """Área de interés en WKT (EPSG:4326)."""
    wkt_4326: str

    @staticmethod
    def from_bbox(lon_min: float, lat_min: float, lon_max: float, lat_max: float) -> "AOI":
        if lon_min >= lon_max or lat_min >= lat_max:
            raise ValueError("BBox inválido (min >= max).")
        wkt = (
            f"POLYGON (({lon_min} {lat_min}, {lon_min} {lat_max}, "
            f"{lon_max} {lat_max}, {lon_max} {lat_min}, {lon_min} {lat_min}))"
        )
        return AOI(wkt)

# =========================
# Restricciones / filtros de búsqueda
# =========================
@dataclass
class Constraints:
    max_cloud: float = 30.0         # % nubosidad máxima
    top_results: int = 5            # límite de resultados
    collection: Collection = "SENTINEL-2"
    product_type: ProductType = "S2MSI2A"  # L2A por defecto

    def validate(self) -> None:
        if not (0.0 <= self.max_cloud <= 100.0):
            raise ValueError("max_cloud debe estar entre 0 y 100.")
        if self.top_results <= 0 or self.top_results > 100:
            raise ValueError("top_results debe estar entre 1 y 100.")

# =========================
# Petición unificada
# =========================
@dataclass
class ImageRequest:
    aoi: AOI
    window: TimeRange
    constraints: Constraints = field(default_factory=Constraints)
    note: Optional[str] = None

    def validate(self) -> None:
        self.constraints.validate()
        if "POLYGON" not in self.aoi.wkt_4326.upper():
            raise ValueError("AOI debe ser un POLYGON WKT (EPSG:4326).")
        _ = self.window.iso_bounds()

    def to_params(self) -> dict:
        self.validate()
        iso_start, iso_end = self.window.iso_bounds()
        return {
            "wkt_aoi": self.aoi.wkt_4326,
            "iso_start": iso_start,
            "iso_end": iso_end,
            "max_cloud": self.constraints.max_cloud,
            "top": self.constraints.top_results,
            "collection": self.constraints.collection,
            "product_type": self.constraints.product_type,
            "note": self.note,
        }

# =========================
# PRESETS de ejemplo (listos para usar)
# =========================
# BBox MADRID (centro—gran vía / retiro aprox.). ¡ANTES TENÍAS PARÍS!
# Formato: [minLon, minLat, maxLon, maxLat]
DEFAULT_BBOX_MADRID = [2.282199998, 48.85999998, 2.282199999, 48.85999999]


# Rango temporal de ejemplo (ajusta a tus fechas)
DEFAULT_TIMERANGE = TimeRange(
    start=date(2025, 8, 1),
    end=date(2025, 11, 4),
)

# Restricciones: nubes <= 20%, devolver 10 resultados, Sentinel-2 L2A
DEFAULT_CONSTRAINTS = Constraints(
    max_cloud=20.0,
    top_results=10,
    collection="SENTINEL-2",
    product_type="S2MSI2A",
)

def madrid_demo_request(note: Optional[str] = "Madrid demo") -> ImageRequest:
    aoi = AOI.from_bbox(*DEFAULT_BBOX_MADRID)
    return ImageRequest(
        aoi=aoi,
        window=DEFAULT_TIMERANGE,
        constraints=DEFAULT_CONSTRAINTS,
        note=note,
    )

if __name__ == "__main__":
    req = madrid_demo_request()
    params = req.to_params()
    print("✅ Petición válida. Parámetros listos para el builder:")
    for k, v in params.items():
        print(f"- {k}: {v}")
