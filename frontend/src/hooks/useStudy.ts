import { useState, useEffect } from "react";
import {
  fetchVideoChapters,
  fetchVideoFlashcards,
  fetchVideoNotes,
  fetchVideoQuiz,
} from "@/services/studyService";

interface UseStudyArtifactResult<T> {
  data: T;
  loading: boolean;
  setData: React.Dispatch<React.SetStateAction<T>>;
}

function useStudyArtifact<T>(
  videoId: string | null,
  statusState: string | undefined,
  fetcher: (id: string) => Promise<T>,
  initialValue: T
): UseStudyArtifactResult<T> {
  const [data, setData] = useState<T>(initialValue);
  const [loading, setLoading] = useState<boolean>(() => Boolean(videoId));

  const [prevKey, setPrevKey] = useState(
    () => `${videoId ?? ""}:${statusState ?? ""}`
  );
  const currentKey = `${videoId ?? ""}:${statusState ?? ""}`;
  if (currentKey !== prevKey) {
    setPrevKey(currentKey);
    setData(initialValue);
    setLoading(Boolean(videoId));
  }

  useEffect(() => {
    if (!videoId) return;

    let active = true;
    fetcher(videoId)
      .then((res) => {
        if (!active) return;
        setData(res);
        setLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setData(initialValue);
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [videoId, statusState, fetcher, initialValue]);

  return { data, loading, setData };
}

export function useVideoChapters(
  videoId: string | null,
  statusState?: string
) {
  const { data: chapters, loading } = useStudyArtifact(
    videoId,
    statusState,
    fetchVideoChapters,
    []
  );
  return { chapters, loading };
}

export function useVideoNotes(
  videoId: string | null,
  statusState?: string
) {
  const { data: notes, loading } = useStudyArtifact(
    videoId,
    statusState,
    fetchVideoNotes,
    null
  );
  return { notes, loading };
}

export function useVideoQuiz(
  videoId: string | null,
  statusState?: string
) {
  const { data: questions, loading } = useStudyArtifact(
    videoId,
    statusState,
    fetchVideoQuiz,
    []
  );
  return { questions, loading };
}

export function useVideoFlashcards(
  videoId: string | null,
  statusState?: string
) {
  const {
    data: cards,
    loading,
    setData: setCards,
  } = useStudyArtifact(
    videoId,
    statusState,
    fetchVideoFlashcards,
    []
  );
  return { cards, loading, setCards };
}
