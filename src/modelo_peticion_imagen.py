# src/modelo_peticion_imagen.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Literal, Tuple

# Tipos aceptados (puedes ampliar)
Collection = Literal["SENTINEL-2"]
ProductType = Literal["S2MSI2A", "S2MSI1C"]

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

@dataclass
class Constraints:
    max_cloud: float = 10.0         # %
    top_results: int = 5
    collection: Collection = "SENTINEL-2"
    product_type: ProductType = "S2MSI2A"  # L2A por defecto

    def validate(self) -> None:
        if not (0.0 <= self.max_cloud <= 100.0):
            raise ValueError("max_cloud debe estar entre 0 y 100.")
        if self.top_results <= 0 or self.top_results > 100:
            raise ValueError("top_results debe estar entre 1 y 100.")

@dataclass
class ImageRequest:
    """Modelo unificado para pedir imágenes."""
    aoi: AOI
    window: TimeRange
    constraints: Constraints = Constraints()
    note: Optional[str] = None      # campo libre por si quieres etiquetar

    def validate(self) -> None:
        self.constraints.validate()
        # Validaciones simples del WKT
        if "POLYGON" not in self.aoi.wkt_4326.upper():
            raise ValueError("AOI debe ser un POLYGON WKT (EPSG:4326).")
        _ = self.window.iso_bounds()  # fuerza validación de fechas

    # Traducción a parámetros que ya usan tus funciones existentes
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
