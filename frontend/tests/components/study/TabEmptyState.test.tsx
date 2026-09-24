import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { TabEmptyState } from "@/components/study/TabEmptyState";
import { BookOpen } from "lucide-react";

describe("TabEmptyState", () => {
  it("renders title and subtitle correctly", () => {
    render(
      <TabEmptyState
        icon={BookOpen}
        title="No notes available"
        subtitle="Study notes will appear once transcription finishes."
      />
    );

    expect(screen.getByText("No notes available")).toBeInTheDocument();
    expect(
      screen.getByText("Study notes will appear once transcription finishes.")
    ).toBeInTheDocument();
  });
});
