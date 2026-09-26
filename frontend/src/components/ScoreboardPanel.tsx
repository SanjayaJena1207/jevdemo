import type { ModelInfo, Scoreboard } from "../types";
import { fmt } from "../api";

export function ScoreboardPanel({
  board,
  models,
  onReset,
}: {
  board: Scoreboard | null;
  models: ModelInfo[];
  onReset: () => void;
}) {
  const byId = Object.fromEntries(models.map((m) => [m.id, m]));
  const rows = [...(board?.rows ?? [])].sort(
    (a, b) => b.wins - a.wins || b.correct - a.correct || (b.avg_tokens_per_sec ?? 0) - (a.avg_tokens_per_sec ?? 0),
  );

  return (
    <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="text-lg font-bold">
          Championship <span className="text-sm font-normal text-zinc-500">({board?.races ?? 0} races)</span>
        </h2>
        <button onClick={onReset} className="text-xs text-zinc-500 hover:text-rose-400">
          reset
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase tracking-wide text-zinc-500">
            <tr>
              <th className="py-2 pr-2">#</th>
              <th className="py-2 pr-2">Model</th>
              <th className="py-2 pr-2 text-right">Wins</th>
              <th className="py-2 pr-2 text-right" title="correct / wrong / errors">C/W/E</th>
              <th className="py-2 pr-2 text-right">Avg tok/s</th>
              <th className="py-2 pr-2 text-right">Avg time</th>
              <th className="py-2 text-right">Total cost</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.model_id} className="border-t border-zinc-800">
                <td className="py-2 pr-2 text-zinc-500">{i + 1}</td>
                <td className="py-2 pr-2">
                  <span
                    className="mr-2 inline-block h-2.5 w-2.5 rounded-full"
                    style={{ background: byId[r.model_id]?.color }}
                  />
                  {byId[r.model_id]?.name ?? r.model_id}
                </td>
                <td className="py-2 pr-2 text-right font-bold tabular-nums">{r.wins}</td>
                <td className="py-2 pr-2 text-right tabular-nums text-zinc-400">
                  {r.correct}/{r.wrong}/{r.errors}
                </td>
                <td className="py-2 pr-2 text-right tabular-nums">{fmt.tps(r.avg_tokens_per_sec)}</td>
                <td className="py-2 pr-2 text-right tabular-nums">{fmt.sec(r.avg_total_time)}</td>
                <td className="py-2 text-right tabular-nums">{fmt.usd(r.total_cost)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
