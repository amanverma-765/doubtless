import { describe, expect, it, vi } from "vitest";
import {
  clearChatHistory,
  fetchChatHistory,
  sendChatMessage,
} from "@/services/chatService";

describe("chatService", () => {
  it("fetchChatHistory returns message list or empty array on error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          messages: [
            { id: 1, role: "user", content: "What is momentum?" },
            { id: 2, role: "assistant", content: "Momentum is mass times velocity." },
          ],
        }),
      })
    );

    const history = await fetchChatHistory("vid-1");
    expect(history).toHaveLength(2);
    expect(history[0].role).toBe("user");

    // Network error returns empty array fallback
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("Network disconnect"))
    );
    const fallback = await fetchChatHistory("vid-1");
    expect(fallback).toEqual([]);
  });

  it("clearChatHistory sends DELETE request", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: "cleared" }),
    });
    vi.stubGlobal("fetch", mockFetch);

    await clearChatHistory("vid-clear");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/chat/vid-clear"),
      expect.objectContaining({ method: "DELETE" })
    );
  });

  it("sendChatMessage posts message and playhead time", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        response: "Gravity acts downward.",
        sources: [],
      }),
    });
    vi.stubGlobal("fetch", mockFetch);

    const res = await sendChatMessage("Which way is gravity?", "vid-1", 42.5);
    expect(res.response).toBe("Gravity acts downward.");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/chat"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          message: "Which way is gravity?",
          video_id: "vid-1",
          current_time: 42.5,
        }),
      })
    );
  });
});
