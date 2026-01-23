'use client';

import { Activity, Network, Settings, MessageCircle, Wifi, WifiOff } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { LanguageToggle } from '@/components/ui/language-toggle';
import { useUIStore } from '@/stores/uiStore';
import { useHealth } from '@/hooks/useApi';
import { cn } from '@/lib/utils';

const navItems = [
  { id: 'live' as const, labelKey: 'live', icon: Activity },
  { id: 'graph' as const, labelKey: 'graph', icon: Network },
];

export function Header() {
  const t = useTranslations('header');
  const { currentView, setCurrentView, setChatOpen, isChatOpen } = useUIStore();
  const { data: healthData, isError, isLoading } = useHealth();

  const isConnected = !isError && healthData?.status === 'healthy';

  return (
    <header className="h-14 border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80">
      <div className="flex h-full items-center justify-between px-4">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="relative flex h-9 w-9 items-center justify-center">
            {/* Gradient background with glow */}
            <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-blue-500 via-blue-600 to-indigo-600 shadow-lg shadow-blue-500/30" />
            {/* Inner highlight */}
            <div className="absolute inset-[1px] rounded-[10px] bg-gradient-to-br from-white/20 to-transparent" />
            <Activity className="relative h-5 w-5 text-white drop-shadow-sm" />
          </div>
          <div className="flex flex-col">
            <span className="text-base font-bold tracking-tight text-foreground">{t('title')}</span>
            <span className="text-[10px] text-muted-foreground -mt-0.5">Industrial AI Platform</span>
          </div>
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
                  'gap-2 text-muted-foreground hover:text-foreground hover:bg-accent',
                  currentView === item.id && 'bg-accent text-foreground'
                )}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{t(item.labelKey)}</span>
              </Button>
            );
          })}
        </nav>

        {/* Right side */}
        <div className="flex items-center gap-1">
          {/* Connection status */}
          <Badge
            variant="outline"
            className={cn(
              'hidden sm:flex items-center gap-1.5 text-xs',
              isLoading && 'text-muted-foreground border-border',
              isConnected && 'text-green-500 border-green-600/50',
              isError && 'text-red-500 border-red-600/50'
            )}
          >
            {isConnected ? (
              <Wifi className="h-3 w-3" />
            ) : (
              <WifiOff className="h-3 w-3" />
            )}
            {isLoading ? t('connecting') : isConnected ? t('connected') : t('disconnected')}
          </Badge>

          {/* Language toggle */}
          <LanguageToggle />

          {/* Mobile chat toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setChatOpen(!isChatOpen)}
            className="md:hidden text-muted-foreground hover:text-foreground"
          >
            <MessageCircle className="h-5 w-5" />
          </Button>

          <Button
            variant="ghost"
            size="icon"
            className="text-muted-foreground hover:text-foreground"
          >
            <Settings className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </header>
  );
}
