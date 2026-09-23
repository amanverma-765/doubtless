export type FeatureTabKey =
  | "doubt"
  | "chapters"
  | "quiz"
  | "notes"
  | "flashcards";

export interface VideoChapter {
  start_time: number;
  end_time: number;
  title: string;
  description: string;
}

export interface VideoChaptersResponse {
  video_id: string;
  chapters: VideoChapter[];
}

export interface VideoNotes {
  video_id: string;
  title?: string | null;
  markdown: string;
}

export interface VideoNotesResponse {
  video_id: string;
  notes: VideoNotes | null;
}

export interface QuizQuestion {
  id: number;
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
  timestamp?: number | null;
}

export interface VideoQuizResponse {
  video_id: string;
  questions: QuizQuestion[];
}

export interface Flashcard {
  id: number;
  front: string;
  back: string;
  category: string;
  timestamp?: number | null;
}

export interface VideoFlashcardsResponse {
  video_id: string;
  cards: Flashcard[];
}
