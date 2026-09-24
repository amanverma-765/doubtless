import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Modal } from "@/components/common/Modal";

describe("Modal", () => {
  it("renders nothing when isOpen is false", () => {
    const { container } = render(
      <Modal isOpen={false} onClose={vi.fn()}>
        <div>Modal Content</div>
      </Modal>
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders children when isOpen is true", () => {
    render(
      <Modal isOpen={true} onClose={vi.fn()}>
        <div>Modal Content</div>
      </Modal>
    );
    expect(screen.getByText("Modal Content")).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", async () => {
    const onClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={onClose}>
        <div>Content</div>
      </Modal>
    );

    const closeBtn = screen.getByRole("button", { name: "Close dialog" });
    await userEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("closes on Escape key press", async () => {
    const onClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={onClose}>
        <div>Content</div>
      </Modal>
    );

    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("does not close on Escape key if isBusy is true", async () => {
    const onClose = vi.fn();
    render(
      <Modal isOpen={true} onClose={onClose} isBusy={true}>
        <div>Content</div>
      </Modal>
    );

    await userEvent.keyboard("{Escape}");
    expect(onClose).not.toHaveBeenCalled();
  });
});
