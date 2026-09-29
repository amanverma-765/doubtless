import { useState, useEffect, useCallback } from "react";
import type { VideoStatus } from "@/types/video";
import { fetchVideoStatus } from "@/services/videoService";

interface UseVideoStatusResult {
  status: VideoStatus | null;
  isLoading: boolean;
  isNotFound: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useVideoStatus(videoId?: string | null): UseVideoStatusResult {
  const targetId = videoId?.trim() || null;

  const [status, setStatus] = useState<VideoStatus | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(() => Boolean(targetId));
  const [isNotFound, setIsNotFound] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [prevTargetId, setPrevTargetId] = useState(targetId);
  if (targetId !== prevTargetId) {
    setPrevTargetId(targetId);
    setStatus(null);
    setIsLoading(Boolean(targetId));
    setIsNotFound(false);
    setError(null);
  }

  const poll = useCallback(async () => {
    if (!targetId) {
      setStatus(null);
      setIsLoading(false);
      return;
    }

    try {
      const current = await fetchVideoStatus(targetId);
      setIsNotFound(current.state === "idle" && !current.id);
      setStatus(current);
      setError(null);
    } catch (err: unknown) {
      const errMsg = (err as Error).message || "Unable to reach video service";
      setError(errMsg);
    } finally {
      setIsLoading(false);
    }
  }, [targetId]);

  useEffect(() => {
    if (!targetId) return;

    let active = true;
    fetchVideoStatus(targetId)
      .then((current) => {
        if (!active) return;
        setIsNotFound(current.state === "idle" && !current.id);
        setStatus(current);
        setError(null);
        setIsLoading(false);
      })
      .catch((err: unknown) => {
        if (!active) return;
        setError((err as Error).message || "Unable to reach video service");
        setIsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [targetId]);

  useEffect(() => {
    if (!targetId || isNotFound) return;
    if (status?.state === "ready" || status?.state === "error") return;

    const interval = setInterval(() => {
      poll();
    }, 1000);

    return () => clearInterval(interval);
  }, [targetId, isNotFound, status?.state, poll]);

  return {
    status,
    isLoading,
    isNotFound,
    error,
    refetch: poll,
  };
}
