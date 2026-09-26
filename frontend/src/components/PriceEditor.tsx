import { useState } from "react";
import type { ModelInfo } from "../types";
import { api } from "../api";

function PriceRow({ m, onSaved }: { m: ModelInfo; onSaved: (m: ModelInfo) => void }) {
  const [input, setInput] = useState(String(m.price_input_per_m));
  const [output, setOutput] = useState(String(m.price_output_per_m));
  const [state, setState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const dirty = Number(input) !== m.price_input_per_m || Number(output) !== m.price_output_per_m;
  const valid = input !== "" && output !== "" && Number(input) >= 0 && Number(output) >= 0;

  const save = async () => {
    setState("saving");
    try {
      onSaved(await api.setPrice(m.id, Number(input), Number(output)));
      setState("saved");
    } catch {
      setState("error");
    }
  };

  const field = "w-20 rounded border border-zinc-700 bg-zinc-950 px-2 py-1 text-right tabular-nums";
  return (
    <tr className="border-t border-zinc-800">
      <td className="py-2 pr-2">{m.name}</td>
      <td className="py-2 pr-2 text-right">
        <input type="number" min={0} step="0.01" className={field} value={input} onChange={(e) => setInput(e.target.value)} />
      </td>
      <td className="py-2 pr-2 text-right">
        <input type="number" min={0} step="0.01" className={field} value={output} onChange={(e) => setOutput(e.target.value)} />
      </td>
      <td className="py-2 text-right">
        {dirty ? (
          <button
            disabled={!valid || state === "saving"}
            onClick={save}
            className="rounded bg-sky-600 px-2 py-1 text-xs font-semibold hover:bg-sky-500 disabled:opacity-40"
          >
            Save
          </button>
        ) : (
          <span className="text-xs text-zinc-500">{state === "saved" ? "saved ✓" : state === "error" ? "failed" : ""}</span>
        )}
      </td>
    </tr>
  );
}

export function PriceEditor({ models, onSaved }: { models: ModelInfo[]; onSaved: (m: ModelInfo) => void }) {
  return (
    <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
      <h2 className="mb-1 text-lg font-bold">Prices</h2>
      <p className="mb-2 text-xs text-zinc-500">USD per 1M tokens. Applied to the next race; saved on the backend.</p>
      <table className="w-full text-sm">
        <thead className="text-left text-xs uppercase tracking-wide text-zinc-500">
          <tr>
            <th className="py-2 pr-2">Model</th>
            <th className="py-2 pr-2 text-right">Input</th>
            <th className="py-2 pr-2 text-right">Output</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {models.map((m) => (
            <PriceRow key={m.id} m={m} onSaved={onSaved} />
          ))}
        </tbody>
      </table>
    </section>
  );
}
