'use client';

import { ReactNode, useSyncExternalStore } from 'react';
import { NextIntlClientProvider, AbstractIntlMessages } from 'next-intl';
import { useLocaleStore } from '@/stores/localeStore';
import { defaultLocale } from '@/i18n/config';

// Import messages statically to avoid dynamic import issues
import koMessages from '../../messages/ko.json';
import enMessages from '../../messages/en.json';

const messages: Record<string, AbstractIntlMessages> = {
  ko: koMessages,
  en: enMessages,
};

// Subscribe to nothing, just used to track if we're on client
const emptySubscribe = () => () => {};
const getSnapshot = () => true;
const getServerSnapshot = () => false;

interface IntlProviderProps {
  children: ReactNode;
}

export function IntlProvider({ children }: IntlProviderProps) {
  const { locale } = useLocaleStore();
  const mounted = useSyncExternalStore(emptySubscribe, getSnapshot, getServerSnapshot);

  // Use default locale for SSR, then switch to stored locale on client
  const effectiveLocale = mounted ? locale : defaultLocale;
  const currentMessages = messages[effectiveLocale] || messages[defaultLocale];

  return (
    <NextIntlClientProvider locale={effectiveLocale} messages={currentMessages} timeZone="Asia/Seoul">
      {children}
    </NextIntlClientProvider>
  );
}
