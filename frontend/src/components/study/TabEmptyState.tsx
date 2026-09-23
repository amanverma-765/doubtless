import type React from "react";

interface TabEmptyStateProps {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  subtitle: string;
}

export const TabEmptyState: React.FC<TabEmptyStateProps> = ({
  icon: Icon,
  title,
  subtitle,
}) => {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-[#faf9f7] select-none">
      <div className="w-12 h-12 rounded-2xl bg-[#f0eee9] border border-[#e5e2db] text-zinc-500 flex items-center justify-center mb-3 shadow-2xs">
        <Icon className="w-6 h-6 text-zinc-400" />
      </div>

      <h3 className="text-sm font-semibold text-zinc-900 mb-1 tracking-tight">
        {title}
      </h3>

      <p className="text-xs text-zinc-500 max-w-xs leading-relaxed text-center">
        {subtitle}
      </p>
    </div>
  );
};
