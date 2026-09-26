import { Fragment, useState } from "react";
import type { ModelInfo, Question, RaceResult } from "../types";
import { fmt } from "../api";

const badge: Record<RaceResult["status"], string> = {
  ok: "bg-emerald-500/15 text-emerald-300",
  wrong: "bg-rose-500/15 text-rose-300",
  error: "bg-zinc-500/20 text-zinc-300",
};

export function ResultsTable({
  results,
  models,
  winner,
  question,
}: {
  results: RaceResult[];
  models: ModelInfo[];
  winner: string | null;
  question: Question;
}) {
  const [open, setOpen] = useState<string | null>(null);
  const byId = Object.fromEntries(models.map((m) => [m.id, m]));
  const rows = [...results].sort((a, b) => {
    const rank = (r: RaceResult) => (r.status === "ok" ? 0 : r.status === "wrong" ? 1 : 2);
    return rank(a) - rank(b) || a.total_time - b.total_time;
  });

  return (
    <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-bold">Race results</h2>
        <div className="text-sm text-zinc-400">
          Expected answer: <span className="font-mono text-zinc-100">{question.answer}</span>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase tracking-wide text-zinc-500">
            <tr>
              <th className="py-2 pr-3">Model</th>
              <th className="py-2 pr-3">Result</th>
              <th className="py-2 pr-3">Answer</th>
              <th className="py-2 pr-3 text-right">TTFT</th>
              <th className="py-2 pr-3 text-right">Total</th>
              <th className="py-2 pr-3 text-right">Tok/s</th>
              <th className="py-2 pr-3 text-right">In tok</th>
              <th className="py-2 pr-3 text-right">Out tok</th>
              <th className="py-2 text-right">Cost</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const m = byId[r.model_id];
              const isOpen = open === r.model_id;
              return (
                <Fragment key={r.model_id}>
                  <tr
                    onClick={() => setOpen(isOpen ? null : r.model_id)}
                    className="cursor-pointer border-t border-zinc-800 hover:bg-zinc-800/40"
                  >
                    <td className="py-2 pr-3">
                      <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full" style={{ background: m?.color }} />
                      {winner === r.model_id && "🏆 "}
                      {m?.name ?? r.model_id}
                    </td>
                    <td className="py-2 pr-3">
                      <span className={`rounded px-2 py-0.5 text-xs ${badge[r.status]}`}>
                        {r.status === "ok" ? "correct" : r.status === "wrong" ? "wrong" : "error"}
                      </span>
                    </td>
                    <td className="max-w-[16rem] truncate py-2 pr-3 font-mono text-xs" title={r.error ?? r.answer}>
                      {r.error ? (
                        <span className="text-zinc-500">{r.error}</span>
                      ) : (
                        <>
                          {r.answer}
                          {r.confidence != null && (
                            <span className="ml-1 text-zinc-500">· {Math.round(r.confidence * 100)}% conf.</span>
                          )}
                        </>
                      )}
                    </td>
                    <td className="py-2 pr-3 text-right tabular-nums">{fmt.sec(r.ttft)}</td>
                    <td className="py-2 pr-3 text-right tabular-nums">{fmt.sec(r.total_time)}</td>
                    <td className="py-2 pr-3 text-right tabular-nums">{fmt.tps(r.tokens_per_sec)}</td>
                    <td className="py-2 pr-3 text-right tabular-nums">{r.prompt_tokens}</td>
                    <td className="py-2 pr-3 text-right tabular-nums">
                      {r.completion_tokens}
                      {!r.usage_reported && r.completion_tokens > 0 && (
                        <span className="text-zinc-500" title="Estimated: provider did not report usage">~</span>
                      )}
                    </td>
                    <td className="py-2 text-right tabular-nums">{fmt.usd(r.cost)}</td>
                  </tr>
                  {isOpen && (
                    <tr key={`${r.model_id}-detail`}>
                      <td colSpan={9} className="pb-3">
                        <pre className="max-h-60 overflow-auto whitespace-pre-wrap rounded bg-zinc-950 p-3 text-xs text-zinc-300">
                          {r.content || r.error || "(no output)"}
                        </pre>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-zinc-500">
        Click a row to see the full response. ~ = token count estimated because the provider didn't report usage.
        Tok/s is measured from the first token to the end of the stream (n/a for Jev, which returns its whole answer at once).
      </p>
    </section>
  );
}
