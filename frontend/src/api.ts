import type { ModelInfo, Scoreboard } from "./types";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  config: () => fetch("/api/config").then((r) => json<{ models: ModelInfo[] }>(r)),
  scoreboard: () => fetch("/api/scoreboard").then((r) => json<Scoreboard>(r)),
  resetScoreboard: () => fetch("/api/scoreboard/reset", { method: "POST" }).then((r) => json<Scoreboard>(r)),
  setPrice: (id: string, input: number, output: number) =>
    fetch(`/api/prices/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ input, output }),
    }).then((r) => json<ModelInfo>(r)),
  raceStreamUrl: (modelIds: string[]) => `/api/race/stream?models=${encodeURIComponent(modelIds.join(","))}`,
};

export const fmt = {
  sec: (v: number | null | undefined) => (v == null ? "—" : `${v.toFixed(2)}s`),
  tps: (v: number | null | undefined) => (v == null ? "—" : v.toFixed(1)),
  usd: (v: number) => (v === 0 ? "$0" : v < 0.01 ? `$${v.toFixed(6)}` : `$${v.toFixed(4)}`),
};
