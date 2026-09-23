import type React from "react";
import {
  MessageSquare,
  ListOrdered,
  HelpCircle,
  FileText,
  Layers,
} from "lucide-react";
import type { FeatureTabKey } from "@/types";

interface FeatureCardsProps {
  activeTab: FeatureTabKey;
  onSelectTab: (tab: FeatureTabKey) => void;
}

interface CardConfig {
  key: FeatureTabKey;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
}

const CARDS: CardConfig[] = [
  {
    key: "doubt",
    title: "Doubt Solver",
    description: "Ask anything about this video",
    icon: MessageSquare,
  },
  {
    key: "chapters",
    title: "Chapters",
    description: "Jump to where the topic changes",
    icon: ListOrdered,
  },
  {
    key: "quiz",
    title: "Quiz",
    description: "Test yourself when the video ends",
    icon: HelpCircle,
  },
  {
    key: "notes",
    title: "Notes",
    description: "Key points from the lecture",
    icon: FileText,
  },
  {
    key: "flashcards",
    title: "Flashcards",
    description: "Revise the important terms",
    icon: Layers,
  },
];

export const FeatureCards: React.FC<FeatureCardsProps> = ({
  activeTab,
  onSelectTab,
}) => {
  return (
    <nav
      aria-label="Workspace feature navigation"
      className="w-full bg-[#f4f2ee] p-1.5 rounded-2xl border border-[#e3e0d8] flex items-center gap-1.5 shadow-2xs overflow-x-auto thin-scrollbar select-none"
    >
      {CARDS.map((card) => {
        const isSelected = activeTab === card.key;
        const IconComponent = card.icon;

        return (
          <button
            key={card.key}
            type="button"
            onClick={() => onSelectTab(card.key)}
            title={card.description}
            className={`flex-1 min-w-[110px] sm:min-w-0 h-11 px-3.5 rounded-xl flex items-center justify-center gap-2.5 transition-all duration-150 select-none cursor-pointer text-[13px] ${
              isSelected
                ? "bg-zinc-900 text-white shadow-xs font-semibold"
                : "bg-transparent text-zinc-600 hover:text-zinc-900 hover:bg-white/80 active:bg-white font-medium"
            }`}
          >
            <IconComponent
              className={`w-4 h-4 shrink-0 transition-colors ${
                isSelected ? "text-white" : "text-zinc-500"
              }`}
            />
            <span className="truncate tracking-tight">{card.title}</span>
          </button>
        );
      })}
    </nav>
  );
};
