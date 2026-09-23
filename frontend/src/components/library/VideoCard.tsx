import type React from "react";
import { Link } from "react-router-dom";
import { Film, Play, Trash2, Clock } from "lucide-react";
import type { VideoItem } from "@/types/video";
import { API_BASE } from "@/constants/config";
import { formatStageLabel } from "@/utils/format";

interface VideoCardProps {
  video: VideoItem;
  onDeleteRequest: (video: VideoItem) => void;
}

export const VideoCard: React.FC<VideoCardProps> = ({
  video,
  onDeleteRequest,
}) => {
  const posterUrl = video.poster
    ? video.poster.startsWith("http")
      ? video.poster
      : `${API_BASE}${video.poster}`
    : null;

  const handleDelete = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onDeleteRequest(video);
  };

  return (
    <Link
      to={`/watch/${video.id}`}
      className="group relative bg-white border border-[#e5e2db] hover:border-zinc-800 rounded-2xl overflow-hidden shadow-2xs hover:shadow-md transition-all duration-200 cursor-pointer flex flex-col"
    >
      {/* 16:9 Thumbnail Poster */}
      <div className="relative aspect-video w-full bg-zinc-900 overflow-hidden flex items-center justify-center">
        {posterUrl ? (
          <img
            src={posterUrl}
            alt={video.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-zinc-900 text-zinc-600">
            <Film className="w-8 h-8 opacity-40" />
          </div>
        )}

        {/* Centered Play overlay */}
        <div className="absolute inset-0 bg-black/20 group-hover:bg-black/35 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="w-10 h-10 rounded-full bg-indigo-600 text-white flex items-center justify-center shadow-md transform scale-90 group-hover:scale-100 transition-transform">
            <Play className="w-4 h-4 fill-white ml-0.5" />
          </div>
        </div>

        {/* Status Badge */}
        <div className="absolute top-2.5 left-2.5">
          {video.status === "ready" ? (
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-600 text-white shadow-2xs">
              Ready
            </span>
          ) : video.status === "error" ? (
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-rose-600 text-white shadow-2xs">
              Failed
            </span>
          ) : (
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-amber-600 text-white shadow-2xs">
              {formatStageLabel(video.stage, video.progress)}
            </span>
          )}
        </div>

        {/* Delete Button */}
        <button
          type="button"
          onClick={handleDelete}
          title="Delete video"
          className="absolute top-2.5 right-2.5 w-7 h-7 rounded-full bg-black/60 hover:bg-rose-600 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all cursor-pointer shadow-xs"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Metadata Footer */}
      <div className="p-3.5 flex flex-col justify-between flex-1 bg-white">
        <h3
          title={video.title}
          className="text-[13.5px] font-semibold text-zinc-900 truncate group-hover:text-indigo-600 transition-colors"
        >
          {video.title}
        </h3>
        <div className="flex items-center gap-1.5 text-[11px] text-zinc-500 mt-1.5 font-medium">
          <Clock className="w-3 h-3 text-zinc-400" />
          <span>
            {video.created_at
              ? new Date(video.created_at).toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                })
              : "Recently"}
          </span>
          <span className="ml-auto text-indigo-600 text-[11px] font-semibold opacity-0 group-hover:opacity-100 transition-opacity">
            Open →
          </span>
        </div>
      </div>
    </Link>
  );
};
