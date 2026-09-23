import type {
  Flashcard,
  QuizQuestion,
  VideoChapter,
  VideoChaptersResponse,
  VideoFlashcardsResponse,
  VideoNotes,
  VideoNotesResponse,
  VideoQuizResponse,
} from "@/types/study";
import { request } from "./client";

export async function fetchVideoChapters(
  videoId: string
): Promise<VideoChapter[]> {
  const data = await request<VideoChaptersResponse>(
    `/api/v1/videos/${encodeURIComponent(videoId)}/chapters`,
    { cache: "no-store" }
  );
  return data.chapters || [];
}

export async function fetchVideoNotes(
  videoId: string
): Promise<VideoNotes | null> {
  const data = await request<VideoNotesResponse>(
    `/api/v1/videos/${encodeURIComponent(videoId)}/notes`,
    { cache: "no-store" }
  );
  return data.notes || null;
}

export async function fetchVideoQuiz(
  videoId: string
): Promise<QuizQuestion[]> {
  const data = await request<VideoQuizResponse>(
    `/api/v1/videos/${encodeURIComponent(videoId)}/quiz`,
    { cache: "no-store" }
  );
  return data.questions || [];
}

export async function fetchVideoFlashcards(
  videoId: string
): Promise<Flashcard[]> {
  const data = await request<VideoFlashcardsResponse>(
    `/api/v1/videos/${encodeURIComponent(videoId)}/flashcards`,
    { cache: "no-store" }
  );
  return data.cards || [];
}
