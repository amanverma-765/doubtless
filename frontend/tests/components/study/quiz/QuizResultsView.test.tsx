import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QuizResultsView } from "@/components/study/quiz/QuizResultsView";

describe("QuizResultsView", () => {
  it("renders score and percentage accurately", () => {
    render(
      <QuizResultsView
        score={4}
        totalQuestions={5}
        onRestart={vi.fn()}
      />
    );

    expect(screen.getByText("Quiz Completed!")).toBeInTheDocument();
    expect(screen.getByText("80% Score")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("/ 5")).toBeInTheDocument();
  });

  it("calls onRestart when Retake Quiz button is clicked", async () => {
    const onRestart = vi.fn();
    render(
      <QuizResultsView
        score={2}
        totalQuestions={5}
        onRestart={onRestart}
      />
    );

    const button = screen.getByRole("button", { name: /retake quiz/i });
    await userEvent.click(button);
    expect(onRestart).toHaveBeenCalledTimes(1);
  });
});
