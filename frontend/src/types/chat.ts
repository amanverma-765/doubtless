export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
  created_at?: string;
}

export interface ChatResponse {
  reply: string;
  video_id: string | null;
}

export interface ChatHistoryResponse {
  video_id: string;
  messages: ChatMessage[];
}

export interface ChatRequest {
  video_id: string;
  message: string;
  current_time?: number | null;
}

export type { FeatureTabKey } from "./study";

export type ChatStreamEvent =
  | { type: "status"; message: string }
  | { type: "token"; delta: string }
  | { type: "done"; reply: string; video_id: string }
  | { type: "error"; message: string; fallback?: string };

export interface ChatStreamCallbacks {
  onStatus?: (status: string) => void;
  onToken?: (tokenDelta: string) => void;
  onDone?: (fullReply: string, videoId: string) => void;
  onError?: (error: string, fallback?: string) => void;
}
