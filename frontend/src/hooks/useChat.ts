import { useState, useEffect, useCallback, useRef } from "react";
import type { ChatMessage } from "@/types/chat";
import { fetchChatHistory, sendChatMessage } from "@/services/chatService";

const INITIAL_GREETING: ChatMessage = {
  role: "assistant",
  content:
    "Hello! I am your video learning assistant. Ask any doubt or question about the lecture or concepts covered in this video.",
};

export function useChat(videoId: string | null) {
  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_GREETING]);
  const [isSending, setIsSending] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const activeVideoIdRef = useRef<string | null>(videoId);

  useEffect(() => {
    activeVideoIdRef.current = videoId;
    let active = true;

    if (!videoId) {
      setMessages([INITIAL_GREETING]);
      return;
    }

    // Reset immediately so previous video's chat doesn't linger
    setMessages([INITIAL_GREETING]);
    setError(null);

    fetchChatHistory(videoId)
      .then((history) => {
        if (!active || activeVideoIdRef.current !== videoId) return;
        if (history.length > 0) {
          setMessages(history);
        } else {
          setMessages([
            {
              role: "assistant",
              content:
                "Video loaded! Feel free to ask any doubt or question about this video.",
            },
          ]);
        }
      })
      .catch(() => {
        if (!active || activeVideoIdRef.current !== videoId) return;
        setMessages([INITIAL_GREETING]);
      });

    return () => {
      active = false;
    };
  }, [videoId]);

  const sendMessage = useCallback(
    async (text: string) => {
      const query = text.trim();
      const targetId = videoId;
      if (!query || !targetId || isSending) return;

      const userMessage: ChatMessage = { role: "user", content: query };
      setMessages((prev) => [...prev, userMessage]);
      setIsSending(true);
      setError(null);

      try {
        const response = await sendChatMessage(query, targetId);
        // Only append if the user is still on the same video
        if (activeVideoIdRef.current === targetId) {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: response.reply },
          ]);
        }
      } catch (err: unknown) {
        if (activeVideoIdRef.current === targetId) {
          const errMsg =
            (err as Error).message || "Failed to get an answer to your doubt.";
          setError(errMsg);
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: `Sorry, an error occurred while solving your doubt: ${errMsg}`,
            },
          ]);
        }
      } finally {
        if (activeVideoIdRef.current === targetId) {
          setIsSending(false);
        }
      }
    },
    [videoId, isSending]
  );

  return {
    messages,
    isSending,
    error,
    sendMessage,
    clearError: () => setError(null),
  };
}
