import type React from "react";
import { useRef } from "react";
import { Link } from "react-router-dom";
import { Upload, ChevronLeft, Trash2 } from "lucide-react";
import type { VideoStatus } from "@/types/video";
import { formatStageLabel } from "@/utils/format";

interface TopBarProps {
  onFileSelect: (file: File) => void;
  status?: VideoStatus | null;
  showBack?: boolean;
  activeTitle?: string | null;
  onDeleteVideo?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  onFileSelect,
  status,
  showBack,
  activeTitle,
  onDeleteVideo,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onFileSelect(e.target.files[0]);
      e.target.value = "";
    }
  };

  return (
    <header className="h-[64px] min-h-[64px] w-full bg-white border-b border-[#e5e2db] px-[var(--side)] flex items-center justify-between z-10 select-none">
      <div className="flex items-center gap-4">
        {showBack && (
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-zinc-800 bg-[#f4f2ee] hover:bg-[#eae7df] border border-[#e3e0d8] rounded-full transition-colors cursor-pointer shadow-2xs"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            <span>Library</span>
          </Link>
        )}

        <Link
          to="/"
          className="flex flex-col justify-center hover:opacity-90 transition-opacity"
        >
          <h1 className="font-serif italic text-[26px] tracking-tight leading-none text-zinc-900 m-0">
            doubtless
          </h1>
          <p className="text-[10px] uppercase tracking-[0.14em] text-zinc-500 mt-1 font-medium truncate max-w-xs">
            {activeTitle ? activeTitle : "Video Streaming & Doubt Solver"}
          </p>
        </Link>
      </div>

      <div className="flex items-center gap-3">
        {status?.state === "processing" && (
          <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200/90 shadow-2xs">
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            {formatStageLabel(status.stage, status.progress)}
          </span>
        )}
        {status?.state === "uploading" && (
          <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200 shadow-2xs">
            <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
            {formatStageLabel("uploading", status.progress)}
          </span>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept="video/*,.mp4,.mkv,.webm,.mov,.avi,.m4v,.ts"
          className="hidden"
          onChange={handleFileChange}
        />

        {onDeleteVideo && (
          <button
            type="button"
            onClick={onDeleteVideo}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-zinc-600 hover:text-rose-600 bg-white border border-[#d5d1c7] hover:border-rose-300 rounded-full hover:bg-rose-50/50 transition-all focus:outline-none focus:ring-2 focus:ring-rose-500/20 cursor-pointer shadow-2xs active:scale-95"
            title="Delete this video"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Delete</span>
          </button>
        )}

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 text-xs font-semibold text-zinc-800 bg-white border border-[#d5d1c7] rounded-full hover:bg-[#f4f2ee] hover:border-zinc-900 transition-all focus:outline-none focus:ring-2 focus:ring-indigo-500/20 cursor-pointer shadow-2xs active:scale-95"
        >
          <Upload className="w-3.5 h-3.5 text-indigo-600" />
          <span>Upload video</span>
        </button>
      </div>
    </header>
  );
};
