import { describe, expect, it, vi } from "vitest";
import {
  fetchVideoChapters,
  fetchVideoFlashcards,
  fetchVideoNotes,
  fetchVideoQuiz,
} from "@/services/studyService";

describe("studyService", () => {
  it("fetchVideoChapters returns chapters list", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          chapters: [
            {
              start_time: 0,
              end_time: 60,
              title: "Intro",
              description: "Getting started",
            },
          ],
        }),
      })
    );

    const chapters = await fetchVideoChapters("vid-1");
    expect(chapters).toHaveLength(1);
    expect(chapters[0].title).toBe("Intro");
  });

  it("fetchVideoNotes returns notes object or null", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          notes: {
            title: "Calculus Summary",
            markdown: "# Derivatives",
          },
        }),
      })
    );

    const notes = await fetchVideoNotes("vid-1");
    expect(notes?.title).toBe("Calculus Summary");
    expect(notes?.markdown).toBe("# Derivatives");
  });

  it("fetchVideoQuiz returns quiz questions", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          questions: [
            {
              id: 1,
              question: "What is derivative of x^2?",
              options: ["x", "2x", "x^3", "2"],
              correct_index: 1,
              explanation: "Power rule gives 2x.",
            },
          ],
        }),
      })
    );

    const quiz = await fetchVideoQuiz("vid-1");
    expect(quiz).toHaveLength(1);
    expect(quiz[0].correct_index).toBe(1);
  });

  it("fetchVideoFlashcards returns flashcards", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          cards: [
            {
              id: 1,
              front: "Force formula",
              back: "F = ma",
              category: "Physics",
            },
          ],
        }),
      })
    );

    const cards = await fetchVideoFlashcards("vid-1");
    expect(cards).toHaveLength(1);
    expect(cards[0].front).toBe("Force formula");
  });
});
