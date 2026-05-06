import { displayValue } from "@/data/mockData";

/** A simple labeled metric card.
 *  Props: label, value (nullable), unit, hint
 */
export default function DataCard({
  label,
  value,
  unit = "",
  hint,
  fallback,
}: {
  label: string;
  value: number | string | null | undefined;
  unit?: string;
  hint?: string;
  fallback?: string;
}) {
  const isPending = value === null || value === undefined;
  return (
    <div className="rounded-xl border border-border bg-card p-5 flex flex-col gap-1">
      <span className="text-xs uppercase tracking-wider text-muted-foreground">{label}</span>
      <span className={`text-2xl font-bold ${isPending ? "text-muted-foreground" : "text-foreground"}`}>
        {displayValue(value as any, unit, fallback)}
      </span>
      {hint && <span className="text-xs text-muted-foreground mt-1">{hint}</span>}
    </div>
  );
}
