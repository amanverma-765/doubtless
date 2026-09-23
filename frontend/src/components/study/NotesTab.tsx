import type React from "react";
import { useState, useMemo } from "react";
import { FileText, Copy, Check, Clock } from "lucide-react";
import type { VideoStatus } from "@/types/video";
import { useVideoNotes } from "@/hooks/useStudy";
import { MarkdownContent } from "@/components/chat/MarkdownContent";
import { TabEmptyState } from "./TabEmptyState";

interface NotesTabProps {
  videoId: string | null;
  currentTime?: number;
  onSeek?: (seconds: number) => void;
  status?: VideoStatus | null;
}

export const NotesTab: React.FC<NotesTabProps> = ({
  videoId,
  onSeek,
  status,
}) => {
  const { notes, loading } = useVideoNotes(videoId, status?.state);
  const [copied, setCopied] = useState<boolean>(false);

  const markdownContent = notes?.markdown;
  const readingTime = useMemo(() => {
    if (!markdownContent) return null;
    const words = markdownContent.trim().split(/\s+/).length;
    return Math.max(1, Math.ceil(words / 180));
  }, [markdownContent]);

  const handleCopy = async () => {
    if (!notes?.markdown) return;
    try {
      await navigator.clipboard.writeText(notes.markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Ignore clipboard write failure
    }
  };

  if (loading && status?.state === "ready") {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-[#faf9f7]">
        <div className="w-8 h-8 rounded-full border-2 border-indigo-600 border-t-transparent animate-spin mb-3" />
        <p className="text-xs text-zinc-500">Loading lecture study notes...</p>
      </div>
    );
  }

  if (!notes || !notes.markdown?.trim()) {
    return (
      <TabEmptyState
        icon={FileText}
        title="Study Notes Not Ready"
        subtitle="Study notes will appear here once the video is processed."
        isProcessing={status?.state !== "ready"}
        stageMessage={status?.stage_message}
      />
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-5 bg-[#faf9f7] thin-scrollbar">
      {/* Document Toolbar Header */}
      <div className="flex items-center justify-between pb-3 mb-4 border-b border-[#e5e2db] select-none">
        <div className="flex items-center gap-2">
          <span className="text-[10.5px] font-semibold uppercase tracking-[0.14em] text-zinc-500 bg-white border border-[#e3e0d8] px-2.5 py-0.5 rounded-full shadow-2xs">
            Study Notes
          </span>
          {readingTime && (
            <span className="text-[11px] text-zinc-400 flex items-center gap-1 font-medium">
              <Clock className="w-3 h-3" />
              {readingTime} min read
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold text-zinc-700 hover:text-zinc-900 bg-[#f4f2ee] hover:bg-[#eae7df] rounded-xl transition-all shadow-2xs hover:shadow-xs active:scale-95 cursor-pointer"
          title="Copy markdown to clipboard"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-600" />
              <span className="text-emerald-700">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5 text-zinc-500" />
              <span>Copy MD</span>
            </>
          )}
        </button>
      </div>

      {/* Clean Markdown Content directly in container */}
      <div className="text-left space-y-3">
        <MarkdownContent
          content={notes.markdown}
          onSeek={onSeek}
          variant="notes"
        />
      </div>
    </div>
  );
};
