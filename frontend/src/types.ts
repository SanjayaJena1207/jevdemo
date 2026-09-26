export interface ModelInfo {
  id: string;
  name: string;
  model: string;
  base_url: string;
  color: string;
  price_input_per_m: number;
  price_output_per_m: number;
  has_key: boolean;
  kind: "chat" | "jev";
}

export interface Question {
  text: string;
  category: "math" | "trivia";
  options: Record<string, string>;
  correct: string;
  answer: string;
}

export type ResultStatus = "ok" | "wrong" | "error";

export interface RaceResult {
  model_id: string;
  status: ResultStatus;
  ttft: number | null;
  total_time: number;
  tokens_per_sec: number | null;
  prompt_tokens: number;
  completion_tokens: number;
  usage_reported: boolean;
  cost: number;
  answer: string;
  confidence: number | null;
  content: string;
  correct: boolean;
  error: string | null;
  finish_order: number;
}

export interface ScoreRow {
  model_id: string;
  races: number;
  wins: number;
  correct: number;
  wrong: number;
  errors: number;
  avg_tokens_per_sec: number | null;
  avg_total_time: number | null;
  total_cost: number;
  total_tokens: number;
}

export interface Scoreboard {
  races: number;
  rows: ScoreRow[];
}

export type LanePhase = "idle" | "waiting" | "running" | "finished" | "crashed" | "stalled";

export interface LaneState {
  phase: LanePhase;
  progress: number; // 0..1
  tokens: number;
  ttft: number | null;
  result?: RaceResult;
}
