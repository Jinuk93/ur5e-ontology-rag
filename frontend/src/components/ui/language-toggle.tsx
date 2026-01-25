'use client';

import { useSyncExternalStore } from 'react';
import { Button } from '@/components/ui/button';
import { useLocaleStore } from '@/stores/localeStore';
import type { Locale } from '@/i18n/config';

// Subscribe to nothing, just used to track if we're on client
const emptySubscribe = () => () => {};
const getSnapshot = () => true;
const getServerSnapshot = () => false;

const localeLabels: Record<Locale, string> = {
  ko: '한국어',
  en: 'EN',
};

export function LanguageToggle() {
  const mounted = useSyncExternalStore(emptySubscribe, getSnapshot, getServerSnapshot);
  const { locale, setLocale } = useLocaleStore();

  const toggleLocale = () => {
    setLocale(locale === 'ko' ? 'en' : 'ko');
  };

  if (!mounted) {
    return (
      <Button variant="ghost" size="sm" className="text-muted-foreground">
        <span className="text-xs">KO</span>
      </Button>
    );
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={toggleLocale}
      className="text-muted-foreground hover:text-foreground"
      title={locale === 'ko' ? 'Switch to English' : '한국어로 전환'}
    >
      <span className="text-xs">{localeLabels[locale]}</span>
    </Button>
  );
}
