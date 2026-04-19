"use client"

import Link from "next/link"
import { useState } from "react"
import { Menu, X, Radar } from "lucide-react"
import { cn } from "@/lib/utils"

const navItems = [
  { label: "Platform", href: "/#platform" },
  { label: "Coverage", href: "/#coverage" },
  { label: "Detection", href: "/#detection" },
  { label: "Pricing", href: "/pricing" },
]

export function SiteHeader() {
  const [open, setOpen] = useState(false)

  return (
    <header className="fixed top-0 left-0 right-0 z-[60]">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 pt-4">
        <div className="flex items-center justify-between gap-4 rounded-full border border-border bg-popover/70 backdrop-blur-xl px-4 sm:px-6 py-2.5 shadow-lg shadow-black/20">
          <Link href="/" className="flex items-center gap-2 font-semibold text-foreground">
            <span className="grid place-items-center w-8 h-8 rounded-full bg-primary text-primary-foreground">
              <Radar className="w-4 h-4" />
            </span>
            <span className="font-mono tracking-tight">
              Global<span className="text-primary">Tracker</span>
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-7 text-sm">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="hidden md:flex items-center gap-2">
            <Link
              href="/login"
              className="px-4 py-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Log in
            </Link>
            <Link
              href="/signup"
              className="px-4 py-1.5 text-sm font-medium rounded-full bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              Sign up
            </Link>
          </div>

          <button
            className="md:hidden grid place-items-center w-9 h-9 rounded-full border border-border bg-card text-foreground"
            onClick={() => setOpen((v) => !v)}
            aria-label="Toggle navigation"
          >
            {open ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>

        {/* Mobile menu */}
        <div
          className={cn(
            "md:hidden overflow-hidden transition-all duration-300",
            open ? "max-h-96 mt-2" : "max-h-0",
          )}
        >
          <div className="rounded-2xl border border-border bg-popover/90 backdrop-blur-xl p-4 shadow-xl">
            <nav className="flex flex-col gap-1">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setOpen(false)}
                  className="px-3 py-2 rounded-md text-sm text-muted-foreground hover:bg-card hover:text-foreground transition-colors"
                >
                  {item.label}
                </Link>
              ))}
              <div className="h-px bg-border my-2" />
              <Link
                href="/login"
                onClick={() => setOpen(false)}
                className="px-3 py-2 rounded-md text-sm text-muted-foreground hover:bg-card hover:text-foreground transition-colors"
              >
                Log in
              </Link>
              <Link
                href="/signup"
                onClick={() => setOpen(false)}
                className="px-3 py-2 rounded-md text-sm font-medium text-center bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                Sign up
              </Link>
            </nav>
          </div>
        </div>
      </div>
    </header>
  )
}
