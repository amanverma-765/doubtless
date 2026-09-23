import { useState, useEffect, useCallback, useRef } from "react";
import type { ChatMessage } from "@/types/chat";
import { fetchChatHistory, streamChatMessage } from "@/services/chatService";

const INITIAL_GREETING: ChatMessage = {
  role: "assistant",
  content:
    "Hello! I am your video learning assistant. Ask any doubt or question about the lecture or concepts covered in this video.",
};

export function useChat(videoId: string | null) {
  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_GREETING]);
  const [isSending, setIsSending] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const activeVideoIdRef = useRef<string | null>(videoId);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    activeVideoIdRef.current = videoId;
    let active = true;

    // Abort any ongoing request for prior video
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsSending(false);
    setStatusMessage(null);

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
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, [videoId]);

  const sendMessage = useCallback(
    async (text: string, currentTime?: number | null) => {
      const query = text.trim();
      const targetId = videoId;
      if (!query || !targetId || isSending) return;

      const userMessage: ChatMessage = { role: "user", content: query };
      setMessages((prev) => [...prev, userMessage]);
      setIsSending(true);
      setStatusMessage("Analyzing video context...");
      setError(null);

      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        await streamChatMessage(
          query,
          targetId,
          currentTime,
          {
            onStatus: (status) => {
              if (activeVideoIdRef.current !== targetId) return;
              setStatusMessage(status);
            },
            onToken: (delta) => {
              if (activeVideoIdRef.current !== targetId) return;
              setStatusMessage(null);
              setMessages((prev) => {
                const last = prev[prev.length - 1];
                if (last && last.role === "assistant") {
                  return [
                    ...prev.slice(0, -1),
                    { ...last, content: last.content + delta },
                  ];
                }
                return [...prev, { role: "assistant", content: delta }];
              });
            },
            onDone: (fullReply) => {
              if (activeVideoIdRef.current !== targetId) return;
              setMessages((prev) => {
                const last = prev[prev.length - 1];
                if (last && last.role === "assistant") {
                  return [
                    ...prev.slice(0, -1),
                    { ...last, content: fullReply },
                  ];
                }
                return [...prev, { role: "assistant", content: fullReply }];
              });
              setStatusMessage(null);
              setIsSending(false);
            },
            onError: (errMsg, fallback) => {
              if (activeVideoIdRef.current !== targetId) return;
              setStatusMessage(null);
              setIsSending(false);

              const content =
                fallback ||
                `Sorry, an error occurred while solving your doubt: ${errMsg}`;
              if (!fallback) {
                setError(errMsg);
              }
              setMessages((prev) => {
                const last = prev[prev.length - 1];
                if (last && last.role === "assistant") {
                  return [
                    ...prev.slice(0, -1),
                    { ...last, content },
                  ];
                }
                return [...prev, { role: "assistant", content }];
              });
            },
          },
          controller.signal
        );
      } catch (err: unknown) {
        if (activeVideoIdRef.current !== targetId) return;
        const msg = (err as Error)?.message || "Failed to send message";
        setError(msg);
      } finally {
        if (activeVideoIdRef.current === targetId) {
          setIsSending(false);
          setStatusMessage(null);
        }
      }
    },
    [videoId, isSending]
  );

  return {
    messages,
    isSending,
    statusMessage,
    error,
    sendMessage,
    clearError: () => setError(null),
  };
}
