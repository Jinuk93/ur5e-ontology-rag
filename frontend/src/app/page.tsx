'use client';

import { Header } from '@/components/layout/Header';
import { SplitView } from '@/components/layout/SplitView';
import { LiveView } from '@/components/live/LiveView';
import { GraphView } from '@/components/graph/GraphView';
import { HistoryView } from '@/components/history/HistoryView';
import { ChatPanel } from '@/components/chat/ChatPanel';
import { useUIStore } from '@/stores/uiStore';

function MainContent() {
  const { currentView } = useUIStore();

  // 모든 뷰를 항상 렌더링하되 CSS로 숨김 (컴포넌트 상태 유지)
  return (
    <div className="h-full relative">
      <div className={currentView === 'live' ? 'h-full' : 'hidden'}>
        <LiveView />
      </div>
      <div className={currentView === 'graph' ? 'h-full' : 'hidden'}>
        <GraphView />
      </div>
      <div className={currentView === 'history' ? 'h-full' : 'hidden'}>
        <HistoryView />
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-slate-950">
      <Header />
      <SplitView
        mainContent={<MainContent />}
        sideContent={<ChatPanel />}
      />
    </div>
  );
}
