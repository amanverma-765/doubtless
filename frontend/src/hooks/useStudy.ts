import { useState, useEffect } from "react";
import type {
  Flashcard,
  QuizQuestion,
  VideoChapter,
  VideoNotes,
} from "@/types/study";
import {
  fetchVideoChapters,
  fetchVideoFlashcards,
  fetchVideoNotes,
  fetchVideoQuiz,
} from "@/services/studyService";

export function useVideoChapters(
  videoId: string | null,
  statusState?: string
) {
  const [chapters, setChapters] = useState<VideoChapter[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!videoId) {
      setChapters([]);
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);

    fetchVideoChapters(videoId)
      .then((data) => {
        if (!active) return;
        setChapters(data);
        setLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setChapters([]);
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [videoId, statusState]);

  return { chapters, loading };
}

export function useVideoNotes(
  videoId: string | null,
  statusState?: string
) {
  const [notes, setNotes] = useState<VideoNotes | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!videoId) {
      setNotes(null);
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);

    fetchVideoNotes(videoId)
      .then((data) => {
        if (!active) return;
        setNotes(data);
        setLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setNotes(null);
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [videoId, statusState]);

  return { notes, loading };
}

export function useVideoQuiz(
  videoId: string | null,
  statusState?: string
) {
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!videoId) {
      setQuestions([]);
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);

    fetchVideoQuiz(videoId)
      .then((data) => {
        if (!active) return;
        setQuestions(data);
        setLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setQuestions([]);
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [videoId, statusState]);

  return { questions, loading };
}

export function useVideoFlashcards(
  videoId: string | null,
  statusState?: string
) {
  const [cards, setCards] = useState<Flashcard[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!videoId) {
      setCards([]);
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);

    fetchVideoFlashcards(videoId)
      .then((data) => {
        if (!active) return;
        setCards(data);
        setLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setCards([]);
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [videoId, statusState]);

  return { cards, loading, setCards };
}
