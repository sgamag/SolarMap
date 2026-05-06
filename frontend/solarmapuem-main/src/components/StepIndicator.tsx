import { Check } from "lucide-react";

export type Step = {
  label: string;
  status: "pendiente" | "activo" | "completado";
  hint?: string;
};

/** Vertical step indicator. */
export default function StepIndicator({ steps }: { steps: Step[] }) {
  return (
    <ol className="space-y-3">
      {steps.map((s, i) => {
        const num = i + 1;
        const isDone = s.status === "completado";
        const isActive = s.status === "activo";
        return (
          <li key={i} className="flex items-start gap-3">
            <div
              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                isDone
                  ? "bg-trust text-trust-foreground"
                  : isActive
                  ? "bg-accent text-accent-foreground"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {isDone ? <Check className="h-4 w-4" /> : num}
            </div>
            <div className="flex-1 pt-0.5">
              <div className={`text-sm font-medium ${isActive ? "text-foreground" : "text-foreground/80"}`}>
                {s.label}
              </div>
              {s.hint && <div className="text-xs text-muted-foreground">{s.hint}</div>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
