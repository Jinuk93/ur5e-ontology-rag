'use client';

import { Activity, Network, History, Settings, MessageCircle, Wifi, WifiOff } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { LanguageToggle } from '@/components/ui/language-toggle';
import { useUIStore } from '@/stores/uiStore';
import { useHealth } from '@/hooks/useApi';
import { cn } from '@/lib/utils';

const navItems = [
  { id: 'live' as const, labelKey: 'live', icon: Activity },
  { id: 'graph' as const, labelKey: 'graph', icon: Network },
  { id: 'history' as const, labelKey: 'history', icon: History },
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
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500">
            <Activity className="h-5 w-5 text-white" />
          </div>
          <span className="text-lg font-semibold text-foreground">{t('title')}</span>
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
        <div className="flex items-center gap-2">
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

          {/* Theme toggle */}
          <ThemeToggle />

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
