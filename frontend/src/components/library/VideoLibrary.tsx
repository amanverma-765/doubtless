import type React from "react";
import { useState } from "react";
import type { VideoItem } from "@/types/video";
import { VideoCard } from "./VideoCard";
import { AddVideoCard } from "./AddVideoCard";
import { DeleteModal } from "./DeleteModal";

interface VideoLibraryProps {
  videos: VideoItem[];
  onUploadFile: (file: File) => void;
  onDeleteVideo: (videoId: string) => Promise<void>;
}

export const VideoLibrary: React.FC<VideoLibraryProps> = ({
  videos,
  onUploadFile,
  onDeleteVideo,
}) => {
  const [videoToDelete, setVideoToDelete] = useState<VideoItem | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  const handleConfirmDelete = async () => {
    if (!videoToDelete) return;
    setIsDeleting(true);
    try {
      await onDeleteVideo(videoToDelete.id);
      setVideoToDelete(null);
    } catch {
      // Handled in parent
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="w-full max-w-7xl mx-auto px-6 py-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h2 className="text-2xl font-serif italic text-[#1f1f1f]">
            Video Library
          </h2>
          <p className="text-xs text-[#6b6b6b] mt-1 font-medium tracking-wide">
            Select a video to start learning and solving doubts, or upload a new one.
          </p>
        </div>
      </div>

      {/* Grid: processed videos first, followed by '+' upload card at the end */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {videos.map((video) => (
          <VideoCard
            key={video.id}
            video={video}
            onDeleteRequest={(v) => setVideoToDelete(v)}
          />
        ))}

        {/* The '+' Add New Video Card at the end */}
        <AddVideoCard onFileSelect={onUploadFile} />
      </div>

      {/* Non-blocking Delete Confirmation Modal */}
      <DeleteModal
        isOpen={videoToDelete !== null}
        videoTitle={videoToDelete?.title || ""}
        onConfirm={handleConfirmDelete}
        onCancel={() => {
          if (!isDeleting) setVideoToDelete(null);
        }}
        isDeleting={isDeleting}
      />
    </div>
  );
};
