import type React from "react";
import { useRef, useEffect } from "react";
import { Bot, Sparkles } from "lucide-react";
import { useChat } from "@/hooks/useChat";
import { ChatMessageItem } from "./ChatMessageItem";
import { ChatInput } from "./ChatInput";
import type { FeatureTabKey } from "@/types";

interface RightPanelProps {
  videoId: string | null;
  activeTab?: FeatureTabKey;
}

const TAB_TITLES: Record<FeatureTabKey, string> = {
  doubt: "DOUBT SOLVER",
  chapters: "CHAPTERS",
  quiz: "QUIZ",
  notes: "NOTES",
  flashcards: "FLASHCARDS",
};

export const RightPanel: React.FC<RightPanelProps> = ({
  videoId,
  activeTab = "doubt",
}) => {
  const { messages, isSending, error, sendMessage } = useChat(videoId);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (activeTab === "doubt") {
      scrollToBottom();
    }
  }, [messages, isSending, activeTab]);

  return (
    <aside className="w-full lg:w-[var(--panel)] h-full bg-white border border-[#e2e0da] rounded-[10px] flex flex-col overflow-hidden shadow-xs">
      {/* Header bar */}
      <div className="bg-[#1f1f1f] text-white text-[11px] font-semibold tracking-[0.14em] px-4 py-3 flex items-center justify-between select-none shrink-0">
        <span>{TAB_TITLES[activeTab]}</span>
        {activeTab === "doubt" && (
          <span className="flex items-center gap-1 text-[10px] text-zinc-400 font-normal">
            <Sparkles className="w-3 h-3 text-indigo-400" />
            AI Assistant
          </span>
        )}
      </div>

      {/* Body */}
      {activeTab === "doubt" ? (
        <div className="flex-1 flex flex-col min-h-0 bg-[#faf9f7]">
          {/* Scrollable chat messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
            {messages.map((m, idx) => (
              <ChatMessageItem key={idx} message={m} />
            ))}

            {isSending && (
              <div className="flex items-start gap-2.5">
                <div className="w-7 h-7 rounded-full bg-[#27272a] text-zinc-200 flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="bg-white border border-[#e4e2dc] rounded-2xl rounded-tl-xs px-3.5 py-2.5 text-[13px] text-zinc-500 shadow-2xs flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse [animation-delay:0.2s]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse [animation-delay:0.4s]" />
                  <span className="ml-1 text-xs">Analyzing video context...</span>
                </div>
              </div>
            )}

            {error && (
              <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs">
                {error}
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Sticky chat input */}
          <ChatInput onSend={sendMessage} disabled={isSending || !videoId} />
        </div>
      ) : (
        /* Empty / Placeholder state for other tabs */
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-[#faf9f7]">
          <div className="w-12 h-12 rounded-xl bg-[#f0eee9] text-[#6b6b6b] flex items-center justify-center mb-3">
            <Sparkles className="w-6 h-6 text-[#4f46e5]" />
          </div>
          <h3 className="text-base font-semibold text-[#1f1f1f] mb-1">
            {TAB_TITLES[activeTab]}
          </h3>
          <p className="text-xs text-[#6b6b6b] max-w-xs leading-relaxed italic">
            This module will automatically generate when your video processing is
            complete.
          </p>
        </div>
      )}
    </aside>
  );
};

