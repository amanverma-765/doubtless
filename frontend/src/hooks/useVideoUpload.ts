import { useState, useRef, useCallback } from "react";
import { uploadVideo } from "@/services/videoService";

interface UseVideoUploadOptions {
  onSuccess?: (videoId: string) => void;
}

export function useVideoUpload(options: UseVideoUploadOptions = {}) {
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  const selectFile = useCallback((file: File) => {
    setError(null);
    setPendingFile(file);
  }, []);

  const clearPendingFile = useCallback(() => {
    if (!isUploading) {
      setPendingFile(null);
      setError(null);
    }
  }, [isUploading]);

  const cancelUpload = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsUploading(false);
    setUploadProgress(0);
    setPendingFile(null);
  }, []);

  const confirmUpload = useCallback(
    async (title: string) => {
      const file = pendingFile;
      if (!file) return;

      setError(null);
      setIsUploading(true);
      setUploadProgress(0);

      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const accepted = await uploadVideo(
          file,
          title,
          (pct) => setUploadProgress(pct),
          controller.signal
        );

        setPendingFile(null);
        setIsUploading(false);
        setUploadProgress(0);
        abortControllerRef.current = null;

        if (accepted.id && options.onSuccess) {
          options.onSuccess(accepted.id);
        }
      } catch (err: unknown) {
        setIsUploading(false);
        setUploadProgress(0);
        if ((err as Error).name === "AbortError") {
          return;
        }
        setError((err as Error).message || "Upload failed");
      }
    },
    [pendingFile, options]
  );

  return {
    pendingFile,
    isUploading,
    uploadProgress,
    error,
    selectFile,
    clearPendingFile,
    cancelUpload,
    confirmUpload,
    clearError: () => setError(null),
  };
}
