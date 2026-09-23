import type React from "react";
import { ListOrdered, Play, Clock } from "lucide-react";
import type { VideoStatus } from "@/types/video";
import { useVideoChapters } from "@/hooks/useStudy";
import { formatTimestamp } from "@/utils/time";
import { TabEmptyState } from "./TabEmptyState";

interface ChaptersTabProps {
  videoId: string | null;
  currentTime?: number;
  onSeek?: (seconds: number) => void;
  status?: VideoStatus | null;
}

export const ChaptersTab: React.FC<ChaptersTabProps> = ({
  videoId,
  currentTime = 0,
  onSeek,
  status,
}) => {
  const { chapters, loading } = useVideoChapters(videoId, status?.state);

  if (loading && status?.state === "ready") {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-[#faf9f7]">
        <div className="w-8 h-8 rounded-full border-2 border-indigo-600 border-t-transparent animate-spin mb-3" />
        <p className="text-xs text-zinc-500">Loading lecture chapters...</p>
      </div>
    );
  }

  if (chapters.length === 0) {
    return (
      <TabEmptyState
        icon={ListOrdered}
        title="Chapters Not Ready"
        subtitle="Chapters will appear here once the video is processed."
        isProcessing={status?.state !== "ready"}
        stageMessage={status?.stage_message}
      />
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-[#faf9f7] thin-scrollbar">
      <div className="flex items-center justify-between pb-2 border-b border-[#e5e2db]">
        <span className="text-[11px] font-semibold tracking-wider text-zinc-500 uppercase">
          Timeline ({chapters.length} chapters)
        </span>
        <span className="text-[11px] text-zinc-400 flex items-center gap-1">
          <Clock className="w-3 h-3" /> Click to jump
        </span>
      </div>

      <div className="space-y-2.5">
        {chapters.map((chap, idx) => {
          const isActive =
            currentTime >= chap.start_time && currentTime < chap.end_time;

          return (
            <div
              key={idx}
              onClick={() => onSeek?.(chap.start_time)}
              className={`group p-3.5 rounded-2xl border transition-all duration-150 cursor-pointer text-left ${
                isActive
                  ? "bg-white border-indigo-300 shadow-xs ring-2 ring-indigo-500/20"
                  : "bg-white/90 border-[#e5e2db] hover:border-indigo-200 hover:bg-white hover:shadow-2xs"
              }`}
            >
              <div className="flex items-start justify-between gap-2 mb-1.5">
                <span
                  className={`text-[13.5px] font-semibold tracking-tight transition-colors line-clamp-1 ${
                    isActive ? "text-indigo-950 font-bold" : "text-zinc-800 group-hover:text-indigo-700"
                  }`}
                >
                  {chap.title}
                </span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSeek?.(chap.start_time);
                  }}
                  className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold shrink-0 transition-all active:scale-95 cursor-pointer select-none ${
                    isActive
                      ? "bg-indigo-600 text-white shadow-2xs"
                      : "bg-indigo-50/90 text-indigo-700 hover:bg-indigo-100 hover:text-indigo-900 border border-indigo-200/80"
                  }`}
                >
                  <span
                    className={`w-3 h-3 rounded-full flex items-center justify-center shrink-0 ${
                      isActive ? "bg-white/20" : "bg-indigo-200/60"
                    }`}
                  >
                    <Play className="w-2 h-2 fill-current ml-0.5" />
                  </span>
                  <span className="tabular-nums">{formatTimestamp(chap.start_time)}</span>
                </button>
              </div>

              {chap.description && (
                <p className="text-[12px] text-zinc-500 line-clamp-2 leading-relaxed">
                  {chap.description}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
