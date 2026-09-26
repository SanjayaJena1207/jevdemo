import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import { Track } from "./components/Track";
import { ResultsTable } from "./components/ResultsTable";
import { ScoreboardPanel } from "./components/ScoreboardPanel";
import { PriceEditor } from "./components/PriceEditor";
import type { LaneState, ModelInfo, Question, RaceResult, Scoreboard } from "./types";

const idleLane = (): LaneState => ({ phase: "idle", progress: 0, tokens: 0, ttft: null });

function phaseFor(r: RaceResult): LaneState["phase"] {
  return r.status === "ok" ? "finished" : r.status === "wrong" ? "crashed" : "stalled";
}

export default function App() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [enabled, setEnabled] = useState<Record<string, boolean>>({});
  const [lanes, setLanes] = useState<Record<string, LaneState>>({});
  const [question, setQuestion] = useState<Question | null>(null);
  const [results, setResults] = useState<RaceResult[] | null>(null);
  const [winner, setWinner] = useState<string | null>(null);
  const [board, setBoard] = useState<Scoreboard | null>(null);
  const [racing, setRacing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [clock, setClock] = useState(0);
  const esRef = useRef<EventSource | null>(null);
  const startRef = useRef(0);

  useEffect(() => {
    api
      .config()
      .then((c) => {
        setModels(c.models);
        setEnabled(Object.fromEntries(c.models.map((m) => [m.id, true])));
      })
      .catch(() => setError("Can't reach the backend. Is it running on port 8010?"));
    api.scoreboard().then(setBoard).catch(() => {});
    return () => esRef.current?.close();
  }, []);

  // race clock
  useEffect(() => {
    if (!racing) return;
    let raf = 0;
    const tick = () => {
      setClock((performance.now() - startRef.current) / 1000);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [racing]);

  const racers = models.filter((m) => enabled[m.id]);

  const startRace = useCallback(() => {
    if (racing || racers.length === 0) return;
    esRef.current?.close();
    setError(null);
    setResults(null);
    setWinner(null);
    setQuestion(null);
    setLanes(Object.fromEntries(racers.map((m) => [m.id, { ...idleLane(), phase: "waiting" }])));
    setRacing(true);
    setClock(0);
    startRef.current = performance.now();

    const es = new EventSource(api.raceStreamUrl(racers.map((m) => m.id)));
    esRef.current = es;

    es.addEventListener("race_start", (e) => {
      setQuestion(JSON.parse((e as MessageEvent).data).question);
      startRef.current = performance.now();
    });
    es.addEventListener("progress", (e) => {
      const d = JSON.parse((e as MessageEvent).data);
      setLanes((prev) => {
        const cur = prev[d.model_id];
        if (!cur || cur.result) return prev;
        return { ...prev, [d.model_id]: { ...cur, phase: "running", progress: d.progress, tokens: d.tokens, ttft: d.ttft } };
      });
    });
    es.addEventListener("finish", (e) => {
      const r: RaceResult = JSON.parse((e as MessageEvent).data);
      setLanes((prev) => {
        const cur = prev[r.model_id] ?? idleLane();
        const phase = phaseFor(r);
        // correct: cross the line; wrong: crash just before it; error: stall where it is
        const progress = phase === "finished" ? 1 : phase === "crashed" ? Math.max(cur.progress, 0.9) : cur.progress;
        return {
          ...prev,
          [r.model_id]: { phase, progress, tokens: r.completion_tokens, ttft: r.ttft, result: r },
        };
      });
      // first correct finisher takes the flag immediately; race_end confirms it
      if (r.status === "ok") setWinner((w) => w ?? r.model_id);
    });
    es.addEventListener("race_end", (e) => {
      const d = JSON.parse((e as MessageEvent).data);
      es.close(); // close before the server ends the stream so EventSource doesn't auto-reconnect
      setResults(d.results);
      setWinner(d.winner);
      setBoard(d.scoreboard);
      setRacing(false);
    });
    es.onerror = () => {
      if (esRef.current !== es || es.readyState === EventSource.CLOSED) return;
      es.close(); // don't let the browser reconnect and start a second race
      setError("Lost connection to the race stream.");
      setRacing(false);
    };
  }, [racing, racers]);

  const updateModel = (m: ModelInfo) => setModels((prev) => prev.map((x) => (x.id === m.id ? { ...x, ...m } : x)));

  const trackModels = racing || results ? models.filter((m) => m.id in lanes) : racers;

  return (
    <div className="mx-auto max-w-6xl space-y-5 px-4 py-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black tracking-tight">
            🏁 LLM <span className="text-orange-500">Grand Prix</span>
          </h1>
          <p className="text-sm text-zinc-400">Same question, all models, streamed concurrently. First correct answer wins.</p>
        </div>
        <div className="flex items-center gap-4">
          {(racing || results) && (
            <div className="font-mono text-2xl tabular-nums text-zinc-300">{clock.toFixed(1)}s</div>
          )}
          <button
            onClick={startRace}
            disabled={racing || racers.length === 0}
            className="rounded-lg bg-orange-600 px-6 py-3 text-lg font-bold shadow-lg shadow-orange-900/40 transition hover:bg-orange-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {racing ? "Racing…" : results ? "Race again" : "Start Race"}
          </button>
        </div>
      </header>

      <div className="flex flex-wrap gap-2">
        {models.map((m) => (
          <label
            key={m.id}
            className={`flex cursor-pointer items-center gap-2 rounded-full border px-3 py-1 text-xs ${
              enabled[m.id] ? "border-zinc-600 bg-zinc-800" : "border-zinc-800 text-zinc-500"
            }`}
          >
            <input
              type="checkbox"
              disabled={racing}
              checked={!!enabled[m.id]}
              onChange={(e) => setEnabled((p) => ({ ...p, [m.id]: e.target.checked }))}
              className="accent-orange-500"
            />
            <span className="h-2 w-2 rounded-full" style={{ background: m.color }} />
            {m.name}
          </label>
        ))}
      </div>

      {error && <div className="rounded-lg border border-rose-800 bg-rose-950/50 p-3 text-sm text-rose-300">{error}</div>}

      <div className="min-h-14 rounded-xl border border-zinc-800 bg-zinc-900 px-4 py-3">
        {question ? (
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <span className="rounded bg-zinc-800 px-2 py-0.5 text-xs uppercase tracking-wide text-zinc-400">
                {question.category}
              </span>
              <span className="text-lg">{question.text}</span>
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {Object.entries(question.options).map(([letter, text]) => {
                const reveal = !racing && results && letter === question.correct;
                return (
                  <div
                    key={letter}
                    className={`rounded-lg border px-3 py-1.5 text-sm ${
                      reveal ? "border-emerald-500 bg-emerald-500/10 text-emerald-200" : "border-zinc-700 bg-zinc-950/50"
                    }`}
                  >
                    <span className="mr-2 font-bold text-zinc-400">{letter}</span>
                    {text}
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <span className="text-zinc-500">{racing ? "Drawing a question…" : "Press Start Race to draw a random question."}</span>
        )}
      </div>

      <Track models={trackModels} lanes={lanes} winner={winner} />

      {!racing && results && question && (
        <ResultsTable results={results} models={models} winner={winner} question={question} />
      )}

      <div className="grid gap-5 lg:grid-cols-[3fr_2fr]">
        <ScoreboardPanel board={board} models={models} onReset={() => api.resetScoreboard().then(setBoard)} />
        <PriceEditor models={models} onSaved={updateModel} />
      </div>
    </div>
  );
}
