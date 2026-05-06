import { displayValue } from "@/data/mockData";

export type Variable = {
  name: string;
  label: string;
  value: number | string | null | undefined;
  unit?: string;
  description?: string;
};

/** Renders a list of variables as a clean table, using displayValue() helper. */
export default function VariableTable({ title, variables }: { title?: string; variables: Variable[] }) {
  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      {title && (
        <div className="px-5 py-3 border-b border-border bg-background-alt">
          <h3 className="text-sm font-bold text-foreground">{title}</h3>
        </div>
      )}
      <table className="w-full text-sm">
        <tbody>
          {variables.map((v) => (
            <tr key={v.name} className="border-b border-border last:border-0">
              <td className="px-5 py-3 align-top">
                <div className="font-mono text-xs text-muted-foreground">{v.name}</div>
                <div className="font-medium text-foreground">{v.label}</div>
                {v.description && <div className="text-xs text-muted-foreground mt-1">{v.description}</div>}
              </td>
              <td className="px-5 py-3 text-right align-top">
                <span className={v.value === null || v.value === undefined ? "text-muted-foreground italic" : "font-bold"}>
                  {displayValue(v.value as any, v.unit ?? "")}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
