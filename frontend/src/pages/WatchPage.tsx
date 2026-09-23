import type React from "react";
import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { AlertCircle, ChevronLeft } from "lucide-react";
import type { MediaPlayerInstance } from "@vidstack/react";
import { TopBar } from "@/components/layout/TopBar";
import { VideoSection } from "@/components/player/VideoSection";
import { FeatureCards } from "@/components/player/FeatureCards";
import { RightPanel } from "@/components/studio/RightPanel";
import { UploadModal } from "@/components/upload/UploadModal";
import { useVideoStatus } from "@/hooks/useVideoStatus";
import { useVideoUpload } from "@/hooks/useVideoUpload";
import { fetchVideoById } from "@/services/videoService";
import type { FeatureTabKey } from "@/types";

export const WatchPage: React.FC = () => {
  const { id: videoId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const playerRef = useRef<MediaPlayerInstance | null>(null);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [videoTitle, setVideoTitle] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<FeatureTabKey>("doubt");

  const handleSeek = useCallback((seconds: number) => {
    if (playerRef.current) {
      playerRef.current.currentTime = seconds;
      playerRef.current.play();
    }
  }, []);

  const { status, isNotFound } = useVideoStatus(videoId);

  const loadVideoMetadata = useCallback(async () => {
    if (!videoId) return;
    try {
      const v = await fetchVideoById(videoId);
      if (v?.title) {
        setVideoTitle(v.title);
      }
    } catch {
      // Backend may be processing or video details already cached
    }
  }, [videoId]);

  useEffect(() => {
    setVideoTitle(null);
    loadVideoMetadata();
  }, [videoId, loadVideoMetadata]);

  // Re-fetch title once video reaches ready status
  useEffect(() => {
    if (status?.state === "ready" && !videoTitle) {
      loadVideoMetadata();
    }
  }, [status?.state, videoTitle, loadVideoMetadata]);

  const {
    pendingFile,
    selectFile,
    clearPendingFile,
    confirmUpload,
    isUploading,
    uploadProgress,
    error: uploadError,
    clearError,
  } = useVideoUpload({
    onSuccess: (newVideoId) => {
      navigate(`/watch/${newVideoId}`);
    },
  });

  if (isNotFound) {
    return (
      <div className="flex flex-col h-screen w-screen bg-[#fcfbfa]">
        <TopBar onFileSelect={selectFile} showBack={true} />
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
          <AlertCircle className="w-12 h-12 text-zinc-400 mb-3" />
          <h2 className="text-xl font-semibold text-zinc-900 mb-1">
            Video Not Found
          </h2>
          <p className="text-sm text-zinc-500 mb-6 max-w-sm">
            The video you are trying to watch does not exist or has been removed.
          </p>
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-5 py-2.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-full transition-all shadow-sm active:scale-95"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Return to Library</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#fcfbfa]">
      <TopBar
        onFileSelect={selectFile}
        status={status}
        showBack={true}
        activeTitle={videoTitle || "Video Workspace"}
      />

      {uploadError && (
        <div className="mx-6 mt-3 p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl flex items-center justify-between text-xs animate-in fade-in shrink-0">
          <span>{uploadError}</span>
          <button
            type="button"
            onClick={clearError}
            className="text-rose-600 hover:text-rose-900 font-semibold ml-4 cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* STUDIO WORKSPACE (Player + Feature Cards + Doubt Panel) */}
      <main className="flex-1 w-full px-[var(--side)] py-3 overflow-hidden flex flex-col lg:flex-row items-start gap-4 justify-between">
        {/* Left Column: Video & Feature Cards */}
        <div className="flex-1 min-w-0 w-full h-full flex flex-col justify-between overflow-hidden">
          <div className="w-full flex-1 flex items-center justify-center min-h-0">
            <VideoSection
              status={status}
              localUploadProgress={null}
              onFileSelect={selectFile}
              videoTitle={videoTitle || undefined}
              playerRef={playerRef}
              onTimeUpdate={setCurrentTime}
            />
          </div>

          <div className="w-full max-w-[var(--vidw)] mx-auto mt-2 shrink-0">
            <FeatureCards activeTab={activeTab} onSelectTab={setActiveTab} />
          </div>
        </div>

        {/* Right Column: Pinned Side Panel */}
        <div className="w-full lg:w-[var(--panel)] h-full shrink-0">
          <RightPanel
            activeTab={activeTab}
            videoId={videoId || null}
            currentTime={currentTime}
            onSeek={handleSeek}
            status={status}
          />
        </div>
      </main>

      {/* Upload Title Modal */}
      <UploadModal
        isOpen={pendingFile !== null}
        file={pendingFile}
        onConfirm={confirmUpload}
        onCancel={clearPendingFile}
        isUploading={isUploading}
        uploadProgress={uploadProgress}
      />
    </div>
  );
};
