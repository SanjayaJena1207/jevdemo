import type { LaneState, ModelInfo } from "../types";
import { fmt } from "../api";

function Car({ color }: { color: string }) {
  return (
    <svg viewBox="0 0 64 28" className="h-7 w-16 drop-shadow-[0_2px_4px_rgba(0,0,0,0.6)]">
      <path d="M4 18 L10 10 Q14 6 22 6 L38 6 Q44 6 49 11 L56 14 Q62 15 62 19 L62 21 L4 21 Z" fill={color} />
      <path d="M17 11 L22 8 L32 8 L32 12 Z M35 8 L40 8 Q44 9 46 12 L35 12 Z" fill="#bae6fd" opacity="0.85" />
      <rect x="54" y="16" width="6" height="2" rx="1" fill="#fef08a" />
      <circle cx="16" cy="21" r="5" fill="#111" stroke="#666" strokeWidth="1.5" />
      <circle cx="49" cy="21" r="5" fill="#111" stroke="#666" strokeWidth="1.5" />
    </svg>
  );
}

function statusLabel(lane: LaneState, isWinner: boolean, m: ModelInfo): { text: string; cls: string } {
  const r = lane.result;
  switch (lane.phase) {
    case "idle":
      return { text: "On the grid", cls: "text-zinc-500" };
    case "waiting":
      return {
        text: m.kind === "jev" ? "Deciding… (decision model: no streaming, answers in one shot)" : "Revving… (waiting for first token)",
        cls: "text-zinc-400",
      };
    case "running":
      return { text: `${lane.tokens} tokens · TTFT ${fmt.sec(lane.ttft)}`, cls: "text-sky-300" };
    case "finished":
      return {
        text: `${isWinner ? "🏆 WINNER · " : "✔ "}#${r?.finish_order} · ${fmt.sec(r?.total_time)} · ${r?.answer}${r?.confidence != null ? ` (${Math.round(r.confidence * 100)}% conf.)` : ""}`,
        cls: isWinner ? "text-amber-300 font-semibold" : "text-emerald-400",
      };
    case "crashed":
      return { text: `💥 Wrong answer: ${r?.answer || "(none)"}`, cls: "text-rose-400" };
    case "stalled":
      return { text: `🛑 Stalled: ${r?.error ?? "error"}`, cls: "text-zinc-400" };
  }
}

export function Track({
  models,
  lanes,
  winner,
}: {
  models: ModelInfo[];
  lanes: Record<string, LaneState>;
  winner: string | null;
}) {
  return (
    <div className="relative overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900 shadow-2xl">
      {/* start & finish lines */}
      <div className="pointer-events-none absolute inset-y-0 left-[12.5rem] w-1 bg-zinc-600/60" />
      <div className="checker pointer-events-none absolute inset-y-0 right-10 w-3 opacity-90" />
      {models.map((m, i) => {
        const lane = lanes[m.id] ?? { phase: "idle", progress: 0, tokens: 0, ttft: null };
        const isWinner = winner === m.id;
        const label = statusLabel(lane, isWinner, m);
        const carCls =
          lane.phase === "running" || lane.phase === "waiting"
            ? "car-running"
            : lane.phase === "crashed"
              ? "car-crashed"
              : lane.phase === "stalled"
                ? "car-stalled"
                : "";
        return (
          <div
            key={m.id}
            className={`flex h-20 items-stretch ${i > 0 ? "border-t-2 border-dashed border-zinc-700" : ""}`}
          >
            <div className="flex w-[12.5rem] shrink-0 flex-col justify-center gap-0.5 bg-zinc-950/60 px-3">
              <div className="flex items-center gap-2">
                <span className="h-3 w-3 rounded-full" style={{ background: m.color }} />
                <span className="truncate text-sm font-semibold">{m.name}</span>
              </div>
              <div className="truncate font-mono text-[11px] text-zinc-500" title={m.model}>
                {m.model}
              </div>
              {!m.has_key && <div className="text-[11px] text-amber-500">no API key</div>}
            </div>
            <div className="track-stripes relative flex-1 bg-zinc-800/70">
              <div
                className="absolute top-1/2 -translate-y-1/2 transition-[left] duration-200 ease-linear"
                style={{ left: `calc(${lane.progress} * (100% - 5.5rem))` }}
              >
                <div className="relative">
                  <div className={carCls}>
                    <Car color={m.color} />
                  </div>
                  {lane.phase === "crashed" && <span className="pop absolute -top-3 left-5 text-2xl">💥</span>}
                  {lane.phase === "stalled" && (
                    <span className="smoke absolute -top-3 -left-1 text-xl">💨</span>
                  )}
                  {isWinner && <span className="pop absolute -top-5 left-6 text-2xl">🏆</span>}
                </div>
              </div>
              <div className={`absolute bottom-1 left-2 right-14 truncate text-xs ${label.cls}`} title={label.text}>
                {label.text}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
