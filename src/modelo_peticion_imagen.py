# src/modelo_peticion_imagen.py
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
        """Devuelve las fechas en formato ISO 8601 (inicio y fin del rango)."""
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
        """
        Crea un POLYGON WKT a partir de un bbox lon/lat.
        OJO: orden lon, lat. Debe cerrarse repitiendo el primer punto.
        """
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
    """Parámetros de filtrado: nubes, número de resultados, etc."""
    max_cloud: float = 10.0         # % nubosidad máxima
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
    """Modelo unificado para pedir imágenes Sentinel."""
    aoi: AOI
    window: TimeRange
    constraints: Constraints = field(default_factory=Constraints)
    note: Optional[str] = None  # etiqueta opcional

    def validate(self) -> None:
        """Comprueba que los parámetros sean coherentes."""
        self.constraints.validate()
        if "POLYGON" not in self.aoi.wkt_4326.upper():
            raise ValueError("AOI debe ser un POLYGON WKT (EPSG:4326).")
        _ = self.window.iso_bounds()  # valida fechas

    def to_params(self) -> dict:
        """Convierte el modelo a un diccionario de parámetros genéricos."""
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

# BBox Madrid centro (rectángulo pequeño de demo)
# (lon_min, lat_min, lon_max, lat_max)
DEFAULT_BBOX_MADRID = (-3.72, 40.40, -3.70, 40.42)

# Rango temporal de ejemplo (ajusta a tus fechas)
DEFAULT_TIMERANGE = TimeRange(
    start=date(2025, 8, 1),
    end=date(2025, 10, 31),
)

# Restricciones: nubes <= 20%, devolver 10 resultados, Sentinel-2 L2A
DEFAULT_CONSTRAINTS = Constraints(
    max_cloud=20.0,
    top_results=10,
    collection="SENTINEL-2",
    product_type="S2MSI2A",
)


def madrid_demo_request(note: Optional[str] = "Madrid demo") -> ImageRequest:
    """Crea una petición de ejemplo para Madrid con los presets de arriba."""
    aoi = AOI.from_bbox(*DEFAULT_BBOX_MADRID)
    return ImageRequest(
        aoi=aoi,
        window=DEFAULT_TIMERANGE,
        constraints=DEFAULT_CONSTRAINTS,
        note=note,
    )


# =========================
# Prueba rápida desde terminal
# =========================
if __name__ == "__main__":
    req = madrid_demo_request()
    params = req.to_params()
    print("✅ Petición válida. Parámetros listos para el builder:")
    for k, v in params.items():
        print(f"- {k}: {v}")
