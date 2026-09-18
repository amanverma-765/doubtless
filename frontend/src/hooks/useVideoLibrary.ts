import { useState, useEffect, useCallback } from "react";
import type { VideoItem } from "@/types/video";
import { fetchVideos, deleteVideo as apiDeleteVideo } from "@/services/videoService";

interface UseVideoLibraryResult {
  videos: VideoItem[];
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  deleteVideo: (id: string) => Promise<void>;
}

export function useVideoLibrary(): UseVideoLibraryResult {
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadVideos = useCallback(async (silent = false) => {
    if (!silent) setIsLoading(true);
    try {
      const list = await fetchVideos();
      setVideos(list);
      setError(null);
    } catch (err: unknown) {
      setError((err as Error).message || "Failed to load videos");
    } finally {
      if (!silent) setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadVideos();
  }, [loadVideos]);

  const hasTranscoding = videos.some(
    (v) => v.status === "processing" || v.status === "uploading"
  );

  // If any video in library is actively processing or uploading, poll periodically
  useEffect(() => {
    if (!hasTranscoding) return;

    const interval = setInterval(() => {
      loadVideos(true);
    }, 1000);

    return () => clearInterval(interval);
  }, [hasTranscoding, loadVideos]);

  const deleteVideo = async (id: string) => {
    // Optimistically update
    setVideos((prev) => prev.filter((v) => v.id !== id));
    try {
      await apiDeleteVideo(id);
    } catch (err: unknown) {
      // Revert on error
      await loadVideos(true);
      throw err;
    }
  };

  return {
    videos,
    isLoading,
    error,
    refresh: () => loadVideos(false),
    deleteVideo,
  };
}
