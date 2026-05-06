import { potentialColor } from "@/data/mockData";

/** Horizontal progress bar 0-1 colored by tier.
 *  Props: value (0-1 or null), label
 */
export default function PotentialBar({ value, label }: { value: number | null | undefined; label?: string }) {
  const pct = value !== null && value !== undefined ? Math.min(100, Math.max(0, value * 100)) : 0;
  const color = value !== null && value !== undefined ? potentialColor(value) : "hsl(var(--muted))";
  const tier =
    value === null || value === undefined
      ? "Pendiente de modelo"
      : value < 0.4
      ? "Potencial bajo"
      : value < 0.65
      ? "Potencial medio"
      : "Potencial alto";

  return (
    <div className="space-y-2">
      {label && <div className="text-sm font-medium text-foreground">{label}</div>}
      <div className="h-4 w-full bg-muted rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{tier}</span>
        <span className="font-bold" style={{ color }}>
          {value !== null && value !== undefined ? value.toFixed(2) : "—"}
        </span>
      </div>
    </div>
  );
}
