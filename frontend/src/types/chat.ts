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
