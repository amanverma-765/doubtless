import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatInput } from "@/components/chat/ChatInput";

describe("ChatInput", () => {
  it("renders textarea with placeholder", () => {
    render(<ChatInput onSend={vi.fn()} placeholder="Type question..." />);
    expect(
      screen.getByPlaceholderText("Type question...")
    ).toBeInTheDocument();
  });

  it("submits message on Enter key press", async () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByRole("textbox");
    await userEvent.type(textarea, "Explain Lenz law{enter}");

    expect(onSend).toHaveBeenCalledWith("Explain Lenz law");
    expect(textarea).toHaveValue("");
  });

  it("does not submit empty or whitespace message", async () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);

    const textarea = screen.getByRole("textbox");
    await userEvent.type(textarea, "   {enter}");

    expect(onSend).not.toHaveBeenCalled();
  });

  it("disables input and button when disabled is true", () => {
    render(<ChatInput onSend={vi.fn()} disabled={true} />);

    expect(screen.getByRole("textbox")).toBeDisabled();
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
