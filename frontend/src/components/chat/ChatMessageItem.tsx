import type React from "react";
import { Bot, User } from "lucide-react";
import type { ChatMessage } from "@/types/chat";
import { MarkdownContent } from "./MarkdownContent";

interface ChatMessageItemProps {
  message: ChatMessage;
  onSeek?: (seconds: number) => void;
}

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({
  message,
  onSeek,
}) => {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex items-start gap-2.5 ${
        isUser ? "flex-row-reverse" : "flex-row"
      }`}
    >
      <div
        className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-xs shadow-2xs ${
          isUser
            ? "bg-indigo-600 text-white"
            : "bg-zinc-900 text-zinc-100 border border-zinc-800"
        }`}
      >
        {isUser ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
      </div>

      <div
        className={`max-w-[88%] rounded-2xl px-4 py-3 text-[13.5px] leading-relaxed break-words shadow-2xs transition-all ${
          isUser
            ? "bg-indigo-600 text-white rounded-tr-xs shadow-xs"
            : "bg-white text-zinc-900 border border-[#e5e2db] rounded-tl-xs"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
        ) : (
          <MarkdownContent
            content={message.content}
            onSeek={onSeek}
            variant="chat"
            className="space-y-3 text-[13.5px] leading-relaxed"
          />
        )}
      </div>
    </div>
  );
};
