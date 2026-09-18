import type React from "react";
import { useRef } from "react";
import { Link } from "react-router-dom";
import { Upload, ChevronLeft } from "lucide-react";
import type { VideoStatus } from "@/types/video";

interface TopBarProps {
  onFileSelect: (file: File) => void;
  status?: VideoStatus | null;
  showBack?: boolean;
  activeTitle?: string | null;
}

export const TopBar: React.FC<TopBarProps> = ({
  onFileSelect,
  status,
  showBack,
  activeTitle,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onFileSelect(e.target.files[0]);
      e.target.value = "";
    }
  };

  return (
    <header className="h-[64px] min-h-[64px] w-full bg-white border-b border-[#e2e0da] px-[var(--side)] flex items-center justify-between z-10">
      <div className="flex items-center gap-4">
        {showBack && (
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-[#1f1f1f] bg-[#f0eee9] hover:bg-[#e4e1d8] rounded-full transition-colors cursor-pointer"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Library</span>
          </Link>
        )}

        <Link
          to="/"
          className="flex flex-col justify-center hover:opacity-85 transition-opacity"
        >
          <h1 className="font-serif italic text-2xl leading-none text-[#1f1f1f] m-0">
            doubtless
          </h1>
          <p className="text-[9.5px] uppercase tracking-[0.15em] text-[#6b6b6b] mt-1 font-medium truncate max-w-xs">
            {activeTitle ? activeTitle : "Video Streaming & Doubt Solver"}
          </p>
        </Link>
      </div>

      <div className="flex items-center gap-3">
        {status?.state === "processing" && (
          <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            Transcoding {Math.round((status.progress || 0) * 100)}%
          </span>
        )}
        {status?.state === "uploading" && (
          <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200">
            <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
            Uploading {Math.round((status.progress || 0) * 100)}%
          </span>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept="video/*,.mp4,.mkv,.webm,.mov,.avi,.m4v,.ts"
          className="hidden"
          onChange={handleFileChange}
        />

        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-[#1f1f1f] bg-white border border-[#d1cec7] rounded-full hover:bg-[#f5f4f0] hover:border-[#1f1f1f] transition-colors focus:outline-none focus:ring-2 focus:ring-[#4f46e5] focus:ring-offset-2 cursor-pointer shadow-xs"
        >
          <Upload className="w-4 h-4 text-[#4f46e5]" />
          <span>Upload video</span>
        </button>
      </div>
    </header>
  );
};
