'use client';

import { ReactNode } from 'react';
import { Sheet, SheetContent } from '@/components/ui/sheet';
import { useUIStore } from '@/stores/uiStore';

interface SplitViewProps {
  mainContent: ReactNode;
  sideContent: ReactNode;
}

export function SplitView({ mainContent, sideContent }: SplitViewProps) {
  const { isChatOpen, setChatOpen } = useUIStore();

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* Main Content - 70% on desktop, 100% on mobile */}
      <main className="flex-1 overflow-auto md:w-[70%]">
        {mainContent}
      </main>

      {/* Side Content (Chat) - 30% on desktop, sheet on mobile */}
      <aside className="hidden md:block md:w-[30%] border-l border-white/10 bg-slate-900/50">
        {sideContent}
      </aside>

      {/* Mobile Sheet for Chat */}
      <Sheet open={isChatOpen} onOpenChange={setChatOpen}>
        <SheetContent side="right" className="w-full sm:max-w-md p-0 bg-slate-900 border-slate-800">
          {sideContent}
        </SheetContent>
      </Sheet>
    </div>
  );
}
