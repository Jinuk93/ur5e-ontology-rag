'use client';

import { Activity, Network, History, Settings, MessageCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useUIStore } from '@/stores/uiStore';
import { cn } from '@/lib/utils';

const navItems = [
  { id: 'live' as const, label: 'Live', icon: Activity },
  { id: 'graph' as const, label: 'Graph', icon: Network },
  { id: 'history' as const, label: 'History', icon: History },
];

export function Header() {
  const { currentView, setCurrentView, setChatOpen, isChatOpen } = useUIStore();

  return (
    <header className="h-14 border-b border-white/10 bg-slate-900/95 backdrop-blur supports-[backdrop-filter]:bg-slate-900/80">
      <div className="flex h-full items-center justify-between px-4">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500">
            <Activity className="h-5 w-5 text-white" />
          </div>
          <span className="text-lg font-semibold text-white">UR5e Monitor</span>
        </div>

        {/* Navigation */}
        <nav className="flex items-center gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <Button
                key={item.id}
                variant="ghost"
                size="sm"
                onClick={() => setCurrentView(item.id)}
                className={cn(
                  'gap-2 text-slate-400 hover:text-white hover:bg-slate-800',
                  currentView === item.id && 'bg-slate-800 text-white'
                )}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{item.label}</span>
              </Button>
            );
          })}
        </nav>

        {/* Right side */}
        <div className="flex items-center gap-2">
          {/* Mobile chat toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setChatOpen(!isChatOpen)}
            className="md:hidden text-slate-400 hover:text-white"
          >
            <MessageCircle className="h-5 w-5" />
          </Button>

          <Button
            variant="ghost"
            size="icon"
            className="text-slate-400 hover:text-white"
          >
            <Settings className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </header>
  );
}
