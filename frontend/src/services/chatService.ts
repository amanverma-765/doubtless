import type {
  ChatMessage,
  ChatResponse,
  ChatHistoryResponse,
} from "@/types/chat";
import { request } from "./client";

export async function fetchChatHistory(videoId: string): Promise<ChatMessage[]> {
  try {
    const data = await request<ChatHistoryResponse>(
      `/api/v1/chat/${encodeURIComponent(videoId)}`,
      { cache: "no-store" }
    );
    return data.messages || [];
  } catch {
    return [];
  }
}

export async function sendChatMessage(
  message: string,
  videoId: string
): Promise<ChatResponse> {
  return request<ChatResponse>("/api/v1/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      video_id: videoId,
    }),
  });
}
