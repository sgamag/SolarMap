# src/solicitud_builder2.py
from datetime import date, timedelta
from modelo_peticion_imagen import AOI, TimeRange, Constraints, ImageRequest

def solicitud_bbox_ultimos_dias(lon_min, lat_min, lon_max, lat_max,
                                dias: int = 30,
                                max_cloud: float = 10.0,
                                top: int = 5,
                                nota: str | None = None) -> ImageRequest:
    aoi = AOI.from_bbox(lon_min, lat_min, lon_max, lat_max)
    end = date.today()
    start = end - timedelta(days=dias)
    window = TimeRange(start=start, end=end)
    cons = Constraints(max_cloud=max_cloud, top_results=top)
    return ImageRequest(aoi=aoi, window=window, constraints=cons, note=nota)

def solicitud_por_wkt_y_rango(wkt_4326: str, start: date, end: date,
                              max_cloud: float = 10.0, top: int = 5,
                              nota: str | None = None) -> ImageRequest:
    aoi = AOI(wkt_4326=wkt_4326)
    window = TimeRange(start=start, end=end)
    cons = Constraints(max_cloud=max_cloud, top_results=top)
    return ImageRequest(aoi=aoi, window=window, constraints=cons, note=nota)
