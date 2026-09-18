import type React from "react";
import { useNavigate } from "react-router-dom";
import { TopBar } from "@/components/layout/TopBar";
import { VideoLibrary } from "@/components/library/VideoLibrary";
import { UploadModal } from "@/components/upload/UploadModal";
import { useVideoLibrary } from "@/hooks/useVideoLibrary";
import { useVideoUpload } from "@/hooks/useVideoUpload";

export const LibraryPage: React.FC = () => {
  const navigate = useNavigate();
  const { videos, deleteVideo } = useVideoLibrary();

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

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#fcfbfa]">
      <TopBar onFileSelect={selectFile} showBack={false} />

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

      {/* VIDEO LIBRARY GRID */}
      <div className="flex-1 overflow-y-auto">
        <VideoLibrary
          videos={videos}
          onUploadFile={selectFile}
          onDeleteVideo={deleteVideo}
        />
      </div>

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
