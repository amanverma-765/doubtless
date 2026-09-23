import type {
  ChatMessage,
  ChatResponse,
  ChatHistoryResponse,
  ChatStreamCallbacks,
  ChatStreamEvent,
} from "@/types/chat";
import { API_BASE } from "@/constants/config";
import { request, parseErrorDetail } from "./client";

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

export async function clearChatHistory(videoId: string): Promise<void> {
  await request(`/api/v1/chat/${encodeURIComponent(videoId)}`, {
    method: "DELETE",
  });
}

export async function sendChatMessage(
  message: string,
  videoId: string,
  currentTime?: number | null
): Promise<ChatResponse> {
  return request<ChatResponse>("/api/v1/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      message,
      video_id: videoId,
      current_time: currentTime !== undefined ? currentTime : null,
    }),
  });
}

export async function streamChatMessage(
  message: string,
  videoId: string,
  currentTime: number | null | undefined,
  callbacks: ChatStreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const url = `${API_BASE}/api/v1/chat`;
  let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({
        message,
        video_id: videoId,
        current_time: currentTime !== undefined ? currentTime : null,
      }),
      signal,
    });

    if (!response.ok) {
      let detail = `Request failed with status ${response.status}`;
      try {
        const errJson = await response.json();
        detail = parseErrorDetail(errJson) || detail;
      } catch {
        // Body not JSON
      }
      callbacks.onError?.(detail);
      return;
    }

    if (!response.body) {
      callbacks.onError?.("No response body available for streaming");
      return;
    }

    reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() ?? "";

      for (const block of blocks) {
        const lines = block.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const jsonText = line.slice(6).trim();
            if (!jsonText) continue;

            try {
              const event: ChatStreamEvent = JSON.parse(jsonText);
              if (event.type === "status") {
                callbacks.onStatus?.(event.message);
              } else if (event.type === "token") {
                callbacks.onToken?.(event.delta);
              } else if (event.type === "done") {
                callbacks.onDone?.(event.reply, event.video_id);
              } else if (event.type === "error") {
                callbacks.onError?.(event.message, event.fallback);
              }
            } catch (err) {
              console.warn("Failed to parse SSE JSON frame:", jsonText, err);
            }
          }
        }
      }
    }
  } catch (err: unknown) {
    if (signal?.aborted) return;
    const msg = (err as Error)?.message || "Streaming connection interrupted";
    callbacks.onError?.(msg);
  } finally {
    reader?.releaseLock();
  }
}

