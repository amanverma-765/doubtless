import type React from "react";
import { useRef, useState } from "react";
import { Upload as UploadIcon, AlertCircle, RefreshCw } from "lucide-react";
import type { VideoStatus } from "@/types/video";
import { API_BASE } from "@/constants/config";
import type { MediaPlayerInstance } from "@vidstack/react";
import { VideoPlayer } from "./VideoPlayer";

interface VideoSectionProps {
  status: VideoStatus | null;
  localUploadProgress: number | null;
  onFileSelect: (file: File) => void;
  videoTitle?: string;
  playerRef?: React.RefObject<MediaPlayerInstance | null>;
  onTimeUpdate?: (time: number) => void;
}

export const VideoSection: React.FC<VideoSectionProps> = ({
  status,
  localUploadProgress,
  onFileSelect,
  videoTitle,
  playerRef,
  onTimeUpdate,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const dragCounterRef = useRef<number>(0);

  const currentState = status?.state || "idle";
  const progress =
    localUploadProgress !== null && currentState === "uploading"
      ? localUploadProgress
      : status?.progress || 0;
  const pctText = `${Math.round(progress * 100)}%`;

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current += 1;
    setIsDragOver(true);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current -= 1;
    if (dragCounterRef.current <= 0) {
      dragCounterRef.current = 0;
      setIsDragOver(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current = 0;
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onFileSelect(e.dataTransfer.files[0]);
    }
  };

  const getPlaylistUrl = () => {
    if (!status?.playlist) return "";
    return status.playlist.startsWith("http")
      ? status.playlist
      : `${API_BASE}${status.playlist}`;
  };

  return (
    <div
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`relative w-full aspect-video max-w-[var(--vidw)] bg-[#191919] rounded-2xl overflow-hidden flex items-center justify-center transition-all shadow-md ${
        isDragOver ? "ring-2 ring-indigo-500 ring-offset-2" : ""
      }`}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept="video/*,.mp4,.mkv,.webm,.mov,.avi,.m4v,.ts"
        className="hidden"
        onChange={(e) => {
          if (e.target.files && e.target.files[0]) {
            onFileSelect(e.target.files[0]);
            e.target.value = "";
          }
        }}
      />

      {/* STATE 1: IDLE DROPZONE */}
      {currentState === "idle" && (
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="w-full h-full flex flex-col items-center justify-center gap-2 text-zinc-300 hover:text-white cursor-pointer group p-6 transition-colors"
        >
          <div className="w-14 h-14 rounded-2xl border border-zinc-750 bg-zinc-850 flex items-center justify-center group-hover:border-indigo-500 group-hover:bg-zinc-800 transition-all shadow-md">
            <UploadIcon className="w-6 h-6 text-zinc-400 group-hover:text-white transition-colors" />
          </div>
          <span className="text-sm font-semibold text-zinc-100 mt-1">
            Click to upload a video
          </span>
          <span className="text-xs text-zinc-400">
            or drop a file here · MP4, MKV, MOV, WebM
          </span>
        </button>
      )}

      {/* STATE 2: UPLOADING */}
      {currentState === "uploading" && (
        <div className="flex flex-col items-center justify-center gap-3 w-full max-w-[320px] px-4">
          <div className="w-full h-1.5 rounded-full bg-zinc-800 overflow-hidden">
            <div
              className="h-full bg-[#4f46e5] rounded-full transition-all duration-200"
              style={{ width: pctText }}
            />
          </div>
          <span className="text-xs text-zinc-400 font-medium tracking-wide">
            Uploading {pctText}
          </span>
        </div>
      )}

      {/* STATE 3: PROCESSING */}
      {currentState === "processing" && (
        <div className="flex flex-col items-center justify-center gap-3.5 w-full max-w-[320px] px-4">
          <div className="w-full h-1.5 rounded-full bg-zinc-800 overflow-hidden">
            <div
              className="h-full bg-[#4f46e5] rounded-full transition-all duration-300"
              style={{ width: progress > 0 ? pctText : "10%" }}
            />
          </div>
          <span className="text-xs text-zinc-300 font-medium tracking-wide text-center">
            {status?.stage_message ||
              (status?.stage === "transcribing"
                ? `Transcribing Speech (GPU) ${pctText}`
                : status?.stage === "indexing"
                ? `Indexing Lecture Vectors ${pctText}`
                : status?.stage === "generating_notes"
                ? `Generating Chapters & Notes ${pctText}`
                : `Transcoding Video (HLS) ${pctText}`)}
          </span>
        </div>
      )}

      {/* STATE 4: READY VIDEO PLAYER */}
      {currentState === "ready" && status?.playlist && (
        <VideoPlayer
          playlistUrl={getPlaylistUrl()}
          title={videoTitle}
          poster={
            status?.id
              ? `${API_BASE}/hls/${status.id}/poster.jpg`
              : undefined
          }
          playerRef={playerRef}
          onTimeUpdate={onTimeUpdate}
        />
      )}

      {/* STATE 5: ERROR */}
      {currentState === "error" && (
        <div className="flex flex-col items-center justify-center gap-3 p-6 text-center">
          <AlertCircle className="w-8 h-8 text-rose-400 mb-1" />
          <p className="text-sm text-rose-200 max-w-sm">
            {status?.error || "Failed to process video."}
          </p>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex items-center gap-2 px-4 py-1.5 text-xs font-medium text-zinc-200 bg-zinc-800 border border-zinc-700 rounded-full hover:border-[#4f46e5] hover:text-white transition-colors cursor-pointer mt-1"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Try another video
          </button>
        </div>
      )}
    </div>
  );
};
