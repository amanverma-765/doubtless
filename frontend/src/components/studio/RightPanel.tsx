import type React from "react";
import { useRef, useEffect, useState } from "react";
import {
  Bot,
  Sparkles,
  MessageSquare,
  Trash2,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { useChat } from "@/hooks/useChat";
import { ChatMessageItem } from "@/components/chat/ChatMessageItem";
import { ChatInput } from "@/components/chat/ChatInput";
import { Modal } from "@/components/common/Modal";
import {
  ChaptersTab,
  NotesTab,
  QuizTab,
  FlashcardsTab,
  TabEmptyState,
} from "@/components/study";
import type { FeatureTabKey } from "@/types";
import type { VideoStatus } from "@/types/video";

export interface RightPanelProps {
  videoId: string | null;
  activeTab?: FeatureTabKey;
  currentTime?: number;
  getCurrentTime?: () => number;
  onSeek?: (seconds: number) => void;
  status?: VideoStatus | null;
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
  currentTime = 0,
  getCurrentTime,
  onSeek,
  status,
}) => {
  const {
    messages,
    isSending,
    isClearing,
    statusMessage,
    error,
    sendMessage,
    clearChat,
  } = useChat(videoId);

  // ponytail: inline live time fallback
  const resolveCurrentTime = () => getCurrentTime?.() ?? currentTime;

  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const isReady = status ? status.state === "ready" : !videoId;
  const hasChatHistory = messages.some((m) => m.role === "user");

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (activeTab === "doubt") {
      scrollToBottom();
    }
  }, [messages, isSending, statusMessage, activeTab]);

  const handleConfirmClear = async () => {
    await clearChat();
    setIsConfirmOpen(false);
  };

  return (
    <aside className="w-full lg:w-[var(--panel)] h-full bg-white border border-[#e2e0da] rounded-2xl flex flex-col overflow-hidden shadow-xs">
      {/* Header bar */}
      <div className="bg-gradient-to-r from-zinc-900 via-zinc-900 to-zinc-800 text-white text-[11px] font-semibold tracking-[0.16em] px-4 py-3 flex items-center justify-between select-none shrink-0 border-b border-zinc-800">
        <span className="tracking-wider uppercase font-semibold text-zinc-200">
          {TAB_TITLES[activeTab]}
        </span>
        {activeTab === "doubt" && (
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 text-[10.5px] px-2.5 py-0.5 rounded-full bg-zinc-800/90 border border-zinc-700/60 text-zinc-300 font-medium">
              <Sparkles className="w-3 h-3 text-indigo-400" />
              AI Tutor
            </span>
            {hasChatHistory && (
              <button
                type="button"
                onClick={() => setIsConfirmOpen(true)}
                disabled={isSending || isClearing}
                className="p-1 text-zinc-400 hover:text-red-400 hover:bg-zinc-800 rounded-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                title="Clear chat history"
                aria-label="Clear chat history"
              >
                {isClearing ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Trash2 className="w-3.5 h-3.5" />
                )}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Body containers with persistent mounting for tab state preservation */}
      <div className={activeTab === "doubt" ? "flex-1 flex flex-col min-h-0 bg-[#faf9f7]" : "hidden"}>
        {!isReady && !hasChatHistory ? (
          <TabEmptyState
            icon={MessageSquare}
            title="Doubt Solver Not Ready"
            subtitle="Doubt resolution will be available once video processing completes."
          />
        ) : (
          /* Scrollable chat messages */
          <div className="flex-1 overflow-y-auto p-4 space-y-3.5 thin-scrollbar flex flex-col">
            {messages.map((m, idx) => (
              <ChatMessageItem key={idx} message={m} onSeek={onSeek} />
            ))}

            {!isReady && (
              <div className="p-3.5 rounded-xl bg-amber-50/80 border border-amber-200/80 flex items-start gap-2.5 text-xs text-amber-900 leading-relaxed shadow-2xs">
                <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse mt-1 shrink-0" />
                <div>
                  <p className="font-semibold text-amber-950">
                    Lecture is currently {status?.state === "uploading" ? "uploading" : "processing"}
                  </p>
                  <p className="text-[11.5px] text-amber-800/90 mt-0.5 leading-relaxed">
                    Doubt solving will activate automatically once AI speech transcription and vector indexing complete.
                  </p>
                </div>
              </div>
            )}

            {isReady && messages.length <= 1 && (
              <div className="mt-auto pt-2 px-1 flex flex-col items-end space-y-2">
                <p className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider text-right">
                  Suggested Questions
                </p>
                <div className="flex flex-col items-end gap-1.5 w-full">
                  {[
                    "Summarize the core concepts covered in this video",
                    "What NCERT textbook chapters relate to this topic?",
                    "Jump to key definitions, formulas, and examples",
                  ].map((promptText, pIdx) => (
                    <button
                      key={pIdx}
                      type="button"
                      onClick={() => sendMessage(promptText, resolveCurrentTime())}
                      disabled={isSending || !videoId}
                      className="w-fit max-w-[88%] text-right text-[12.5px] text-zinc-700 bg-white hover:bg-indigo-50/70 border border-[#e2e0da] hover:border-indigo-200 px-3 py-2 rounded-xl transition-all shadow-2xs hover:shadow-xs cursor-pointer leading-snug"
                    >
                      {promptText}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {isSending && statusMessage && (
              <div className="flex items-start gap-2.5 animate-in fade-in duration-200">
                <div className="w-7 h-7 rounded-full bg-zinc-900 text-white border border-zinc-800 flex items-center justify-center shrink-0 shadow-2xs">
                  <Bot className="w-3.5 h-3.5" />
                </div>
                <div className="bg-white border border-indigo-100/90 rounded-2xl rounded-tl-xs px-3.5 py-2 text-[12.5px] text-zinc-700 shadow-2xs flex items-center gap-2">
                  <span className="flex gap-1 items-center">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse [animation-delay:0.2s]" />
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse [animation-delay:0.4s]" />
                  </span>
                  <span className="text-xs text-indigo-900 font-medium">{statusMessage}</span>
                </div>
              </div>
            )}

            {error && (
              <div className="p-2.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs">
                {error}
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Sticky chat input */}
        <ChatInput
          onSend={(text) => sendMessage(text, resolveCurrentTime())}
          disabled={isSending || !videoId || !isReady}
          placeholder={
            !isReady
              ? "Doubt solver will unlock once video processing completes…"
              : undefined
          }
        />
      </div>

      <div className={activeTab === "chapters" ? "flex-1 flex flex-col min-h-0" : "hidden"}>
        <ChaptersTab
          videoId={videoId}
          currentTime={currentTime}
          onSeek={onSeek}
          status={status}
        />
      </div>

      <div className={activeTab === "notes" ? "flex-1 flex flex-col min-h-0" : "hidden"}>
        <NotesTab
          videoId={videoId}
          currentTime={currentTime}
          onSeek={onSeek}
          status={status}
        />
      </div>

      <div className={activeTab === "quiz" ? "flex-1 flex flex-col min-h-0" : "hidden"}>
        <QuizTab
          videoId={videoId}
          currentTime={currentTime}
          onSeek={onSeek}
          status={status}
        />
      </div>

      <div className={activeTab === "flashcards" ? "flex-1 flex flex-col min-h-0" : "hidden"}>
        <FlashcardsTab
          videoId={videoId}
          currentTime={currentTime}
          onSeek={onSeek}
          status={status}
        />
      </div>

      {/* Clear Chat Confirmation Modal */}
      <Modal
        isOpen={isConfirmOpen}
        onClose={() => {
          if (!isClearing) setIsConfirmOpen(false);
        }}
        isBusy={isClearing}
        maxWidth="max-w-sm"
      >
        <div className="space-y-4">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-full bg-red-50 flex items-center justify-center shrink-0 text-red-600">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-zinc-900">
                Clear Chat History?
              </h3>
              <p className="text-xs text-zinc-500 mt-1 leading-relaxed">
                This will permanently delete all questions and tutor responses for this video lecture. This action cannot be undone.
              </p>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-2">
            <button
              type="button"
              onClick={() => setIsConfirmOpen(false)}
              disabled={isClearing}
              className="px-3 py-1.5 text-xs font-medium text-zinc-600 hover:text-zinc-800 hover:bg-zinc-100 rounded-lg transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleConfirmClear}
              disabled={isClearing}
              className="px-3.5 py-1.5 text-xs font-medium bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors flex items-center gap-1.5 shadow-xs disabled:opacity-50"
            >
              {isClearing ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Clearing...
                </>
              ) : (
                <>
                  <Trash2 className="w-3.5 h-3.5" />
                  Clear Chat
                </>
              )}
            </button>
          </div>
        </div>
      </Modal>
    </aside>
  );
};
