'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { Header } from '@/components/layout/Header';
import { SplitView } from '@/components/layout/SplitView';
import { LiveView } from '@/components/live/LiveView';
import { GraphView } from '@/components/graph/GraphView';
import { HistoryView } from '@/components/history/HistoryView';
import { ChatPanel } from '@/components/chat/ChatPanel';
import { useUIStore } from '@/stores/uiStore';
import { pageTransition } from '@/lib/animations';

function MainContent() {
  const { currentView } = useUIStore();

  const renderView = () => {
    switch (currentView) {
      case 'live':
        return <LiveView />;
      case 'graph':
        return <GraphView />;
      case 'history':
        return <HistoryView />;
      default:
        return <LiveView />;
    }
  };

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={currentView}
        initial="hidden"
        animate="visible"
        exit="exit"
        variants={pageTransition}
        className="h-full"
      >
        {renderView()}
      </motion.div>
    </AnimatePresence>
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
