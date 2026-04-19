'use client'

import Link from 'next/link'
import { Radar } from 'lucide-react'

import { AnimatedSignIn } from '@/components/ui/sign-in'

export function LoginView() {
  return (
    <div className="relative min-h-screen">
      <header className="pointer-events-none fixed top-0 left-0 z-50 flex w-full justify-center p-4">
        <Link
          href="/"
          className="pointer-events-auto inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)]/95 px-4 py-2 text-sm text-[var(--color-heading)] shadow-sm backdrop-blur-md transition-colors hover:border-[var(--color-text-primary)]/50"
        >
          <Radar className="size-4 text-[var(--color-text-primary)]" aria-hidden />
          <span className="font-geist tracking-tight">
            Global<span className="text-[var(--color-text-primary)]">Tracker</span>
          </span>
        </Link>
      </header>
      <AnimatedSignIn />
    </div>
  )
}
