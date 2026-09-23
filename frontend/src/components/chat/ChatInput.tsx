import type React from "react";
import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  disabled,
  placeholder = "Ask a doubt about this video… (Shift+Enter for newline)",
}) => {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea based on scrollHeight
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      const nextHeight = Math.min(textareaRef.current.scrollHeight, 120);
      textareaRef.current.style.height = `${nextHeight}px`;
    }
  }, [input]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSend();
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="p-3 bg-white border-t border-[#e5e2db] flex flex-col gap-1.5"
    >
      <div className="flex items-end gap-2 bg-[#faf9f7] border border-[#d5d1c7] rounded-xl p-1.5 focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-500/20 focus-within:bg-white transition-all shadow-2xs">
        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          className="flex-1 text-[13.5px] px-2.5 py-1 bg-transparent text-zinc-900 placeholder:text-zinc-400 focus:outline-none disabled:opacity-50 resize-none max-h-[120px] leading-relaxed"
        />
        <button
          type="submit"
          disabled={!input.trim() || disabled}
          className="h-8 w-8 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed transition-all flex items-center justify-center cursor-pointer shadow-2xs shrink-0"
          title="Send message (Enter)"
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </div>
      <div className="flex items-center justify-between px-1 text-[10.5px] text-zinc-400 select-none">
        <span>Shift+Enter for new line</span>
        <span>Enter to send</span>
      </div>
    </form>
  );
};
