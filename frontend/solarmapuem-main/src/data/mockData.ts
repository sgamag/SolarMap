// Mock data for SolarMap. Replace with real backend when connecting API.
// TODO: fetch('/api/tiles')

export type TilePotential = {
  id: string;
  row: number;
  col: number;
  potential: number; // 0-1
};

// 6x6 grid centered around Madrid; ~8x8 km tiles
export const MADRID_CENTER: [number, number] = [40.415, -3.684];
export const TILE_DEG = 0.072; // ~8 km approx in degrees lat

const seededValues = [
  0.42, 0.55, 0.61, 0.73, 0.81, 0.69,
  0.38, 0.51, 0.66, 0.78, 0.85, 0.72,
  0.45, 0.58, 0.7, 0.82, 0.91, 0.74,
  0.5, 0.62, 0.74, 0.86, 0.93, 0.79,
  0.41, 0.53, 0.67, 0.77, 0.84, 0.7,
  0.36, 0.48, 0.6, 0.71, 0.79, 0.65,
];

export const mockTiles: TilePotential[] = Array.from({ length: 36 }, (_, i) => {
  const row = Math.floor(i / 6);
  const col = i % 6;
  return {
    id: `tile_${String(row + 1).padStart(2, "0")}_${String(col + 1).padStart(2, "0")}`,
    row,
    col,
    potential: seededValues[i],
  };
});

// Get tile bounds [[south, west],[north, east]]
export function tileBounds(tile: TilePotential): [[number, number], [number, number]] {
  const [centerLat, centerLng] = MADRID_CENTER;
  const startLat = centerLat - 3 * TILE_DEG;
  const startLng = centerLng - 3 * TILE_DEG;
  const south = startLat + tile.row * TILE_DEG;
  const north = south + TILE_DEG;
  const west = startLng + tile.col * TILE_DEG;
  const east = west + TILE_DEG;
  return [
    [south, west],
    [north, east],
  ];
}

export function potentialColor(p: number): string {
  if (p < 0.4) return "#2D6FE8";
  if (p < 0.65) return "#F5B400";
  return "#E8970A";
}

// Mock roof polygons (small rectangles within Madrid bbox)
// TODO: fetch('/api/roofs?tile_id=...')
export type RoofPolygon = {
  id: string;
  potential: number;
  area: number;
  coords: [number, number][]; // ring
};

function roofRect(lat: number, lng: number, dLat = 0.0006, dLng = 0.0008): [number, number][] {
  return [
    [lat, lng],
    [lat + dLat, lng],
    [lat + dLat, lng + dLng],
    [lat, lng + dLng],
  ];
}

export const mockRoofs: RoofPolygon[] = [
  { id: "roof_001", potential: 0.82, area: 124, coords: roofRect(40.418, -3.7) },
  { id: "roof_002", potential: 0.74, area: 98, coords: roofRect(40.42, -3.69) },
  { id: "roof_003", potential: 0.55, area: 210, coords: roofRect(40.41, -3.68) },
  { id: "roof_004", potential: 0.91, area: 156, coords: roofRect(40.425, -3.705) },
  { id: "roof_005", potential: 0.36, area: 75, coords: roofRect(40.405, -3.66) },
  { id: "roof_006", potential: 0.68, area: 142, coords: roofRect(40.43, -3.67) },
  { id: "roof_007", potential: 0.79, area: 188, coords: roofRect(40.412, -3.71) },
  { id: "roof_008", potential: 0.62, area: 95, coords: roofRect(40.4, -3.69) },
  { id: "roof_009", potential: 0.85, area: 220, coords: roofRect(40.435, -3.69) },
  { id: "roof_010", potential: 0.48, area: 110, coords: roofRect(40.408, -3.65) },
  { id: "roof_011", potential: 0.71, area: 165, coords: roofRect(40.422, -3.715) },
  { id: "roof_012", potential: 0.58, area: 88, coords: roofRect(40.44, -3.68) },
  { id: "roof_013", potential: 0.93, area: 245, coords: roofRect(40.428, -3.66) },
  { id: "roof_014", potential: 0.66, area: 134, coords: roofRect(40.395, -3.7) },
  { id: "roof_015", potential: 0.77, area: 178, coords: roofRect(40.415, -3.72) },
];

// Sparkline mock series (12 monthly values 0-1)
export const mockSparklines = {
  rad_norm: [0.42, 0.5, 0.61, 0.74, 0.85, 0.92, 0.95, 0.9, 0.78, 0.62, 0.48, 0.4],
  pen_nube: [0.65, 0.7, 0.75, 0.82, 0.88, 0.91, 0.94, 0.92, 0.85, 0.78, 0.7, 0.66],
  pen_temp: [0.95, 0.93, 0.9, 0.85, 0.78, 0.7, 0.62, 0.66, 0.78, 0.86, 0.92, 0.96],
  horas_norm: [0.45, 0.55, 0.65, 0.78, 0.88, 0.95, 0.98, 0.92, 0.8, 0.65, 0.5, 0.42],
};

// Helper for displaying nullable values
export function displayValue(val: number | string | null | undefined, unit = "", fallback = "Pendiente de conexión"): string {
  if (val === null || val === undefined) return fallback;
  return `${val}${unit ? " " + unit : ""}`;
}
