'use client';

import { Toaster as Sonner } from 'sonner';

type ToasterProps = React.ComponentProps<typeof Sonner>;

export function Toaster({ ...props }: ToasterProps) {
  return (
    <Sonner
      theme="dark"
      className="toaster group"
      position="top-center"
      offset="60px"
      visibleToasts={2}
      toastOptions={{
        classNames: {
          toast:
            'group toast group-[.toaster]:bg-slate-800/90 group-[.toaster]:text-slate-100 group-[.toaster]:border group-[.toaster]:shadow-lg group-[.toaster]:text-xs group-[.toaster]:py-1.5 group-[.toaster]:px-3 group-[.toaster]:min-h-0 group-[.toaster]:rounded-md group-[.toaster]:backdrop-blur-sm group-[.toaster]:max-w-[280px]',
          description: 'group-[.toast]:text-slate-400 group-[.toast]:text-[10px]',
          actionButton:
            'group-[.toast]:bg-slate-600 group-[.toast]:text-slate-200 group-[.toast]:text-[10px] group-[.toast]:py-0.5 group-[.toast]:px-2',
          cancelButton:
            'group-[.toast]:bg-slate-700 group-[.toast]:text-slate-400 group-[.toast]:text-[10px]',
          error:
            'group-[.toaster]:bg-red-900/95 group-[.toaster]:border-red-500/70 group-[.toaster]:text-red-100 [&_svg]:text-red-400',
          warning:
            'group-[.toaster]:bg-red-900/95 group-[.toaster]:border-red-500/70 group-[.toaster]:text-red-100 [&_svg]:text-red-400',
          success:
            'group-[.toaster]:bg-green-900/95 group-[.toaster]:border-green-500/70 group-[.toaster]:text-green-100 [&_svg]:text-green-400',
          info:
            'group-[.toaster]:bg-blue-900/95 group-[.toaster]:border-blue-500/70 group-[.toaster]:text-blue-100 [&_svg]:text-blue-400',
        },
        duration: 2500,
      }}
      expand={false}
      richColors={false}
      closeButton={false}
      gap={6}
      {...props}
    />
  );
}
