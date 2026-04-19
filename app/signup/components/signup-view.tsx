'use client'

import * as React from 'react'
import Image from 'next/image'
import Link from 'next/link'
import { ChevronDown, Radar } from 'lucide-react'

import { AppAuthInput } from '@/components/ui/login-1'
import { authInputClassName } from '@/lib/auth-field-classes'
import { cn } from '@/lib/utils'

import { INDIA_STATES } from '@/app/signup/lib/india-states'

export function SignupView() {
  const [mousePosition, setMousePosition] = React.useState({ x: 0, y: 0 })
  const [isHovering, setIsHovering] = React.useState(false)
  const [formError, setFormError] = React.useState<string | null>(null)

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const r = e.currentTarget.getBoundingClientRect()
    setMousePosition({
      x: e.clientX - r.left,
      y: e.clientY - r.top,
    })
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    const pw = String(fd.get('password') ?? '')
    const confirm = String(fd.get('confirmPassword') ?? '')
    if (pw !== confirm) {
      setFormError('Passwords do not match.')
      return
    }
    setFormError(null)
  }

  return (
    <div className="relative min-h-screen">
      <header className="pointer-events-none fixed top-0 left-0 z-50 flex w-full justify-center p-4">
        <Link
          href="/"
          className="pointer-events-auto inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)]/95 px-4 py-2 text-sm text-[var(--color-heading)] shadow-sm backdrop-blur-md transition-colors hover:border-[var(--color-text-primary)]/50"
        >
          <Radar className="size-4 text-[var(--color-text-primary)]" aria-hidden />
          <span className="font-mono tracking-tight">
            Global<span className="text-[var(--color-text-primary)]">Tracker</span>
          </span>
        </Link>
      </header>

      <div className="flex min-h-screen w-full items-center justify-center bg-[var(--color-bg)] p-4 pt-24 pb-12">
        <div className="card flex min-h-[600px] w-[90%] max-w-5xl flex-col justify-between overflow-hidden rounded-[var(--rounded-lg)] border border-[var(--color-border)] bg-[var(--color-muted-surface)]/40 shadow-[var(--shadow-xl)] md:w-[80%] lg:w-[70%] lg:flex-row">
          <div
            className="relative h-full w-full overflow-hidden px-4 py-8 lg:w-1/2 lg:px-12"
            onMouseMove={handleMouseMove}
            onMouseEnter={() => setIsHovering(true)}
            onMouseLeave={() => setIsHovering(false)}
          >
            <div
              className={cn(
                'pointer-events-none absolute h-[500px] w-[500px] rounded-full bg-gradient-to-r from-[#2563eb]/25 via-[#3b82f6]/20 to-[#6366f1]/25 blur-3xl transition-opacity duration-200',
                isHovering ? 'opacity-100' : 'opacity-0',
              )}
              style={{
                transform: `translate(${mousePosition.x - 250}px, ${mousePosition.y - 250}px)`,
                transition: 'transform 0.1s ease-out',
              }}
            />

            <div className="relative z-10 mx-auto flex w-full max-w-md flex-col justify-center py-4 lg:min-h-[560px]">
              <form
                className="flex flex-col gap-5 text-center"
                onSubmit={handleSubmit}
              >
                <div className="space-y-1">
                  <h1 className="text-3xl font-extrabold text-[var(--color-heading)] md:text-4xl">
                    Create account
                  </h1>
                  <p className="text-sm text-[var(--color-text-secondary)]">
                    Join GlobalTracker — India operations ready.
                  </p>
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <AppAuthInput
                    label="First name"
                    name="firstName"
                    autoComplete="given-name"
                    placeholder="First name"
                    required
                  />
                  <AppAuthInput
                    label="Last name"
                    name="lastName"
                    autoComplete="family-name"
                    placeholder="Last name"
                    required
                  />
                </div>

                <AppAuthInput
                  label="Phone number"
                  name="phone"
                  type="tel"
                  autoComplete="tel"
                  placeholder="+91 …"
                  required
                />

                <AppAuthInput
                  label="Email address"
                  name="email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@company.com"
                  required
                />

                <div className="text-left">
                  <label className="mb-2 block text-sm text-[var(--color-heading)]">
                    Country
                  </label>
                  <div
                    className="flex h-12 items-center rounded-[var(--rounded-lg)] border-2 border-[var(--color-border)] bg-[var(--color-muted-surface)] px-4 text-sm text-[var(--color-heading)]"
                    aria-readonly
                  >
                    India
                  </div>
                  <input type="hidden" name="country" value="India" />
                </div>

                <div className="relative text-left">
                  <label
                    htmlFor="signup-state"
                    className="mb-2 block text-sm text-[var(--color-heading)]"
                  >
                    State (India)
                  </label>
                  <div className="relative">
                    <select
                      id="signup-state"
                      name="state"
                      required
                      defaultValue=""
                      className={cn(
                        authInputClassName,
                        'cursor-pointer appearance-none pr-10 font-normal',
                      )}
                    >
                      <option value="" disabled>
                        Select state / UT
                      </option>
                      {INDIA_STATES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                    <ChevronDown
                      className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-[var(--color-text-secondary)]"
                      aria-hidden
                    />
                  </div>
                </div>

                <AppAuthInput
                  label="Password"
                  name="password"
                  type="password"
                  autoComplete="new-password"
                  placeholder="Create a password"
                  required
                  minLength={10}
                />

                <AppAuthInput
                  label="Confirm password"
                  name="confirmPassword"
                  type="password"
                  autoComplete="new-password"
                  placeholder="Confirm password"
                  required
                  minLength={10}
                />

                {formError ? (
                  <p className="text-destructive text-left text-sm" role="alert">
                    {formError}
                  </p>
                ) : null}

                <div className="flex justify-center pt-1">
                  <button
                    type="submit"
                    className="group/button relative inline-flex cursor-pointer items-center justify-center overflow-hidden rounded-[var(--rounded-lg)] bg-[var(--color-border)] px-6 py-2 text-sm font-medium text-white transition-all duration-300 ease-in-out hover:scale-[1.02] hover:shadow-lg hover:shadow-[var(--color-text-primary)]"
                  >
                    <span className="relative z-10 px-2 py-1">Create account</span>
                    <div className="absolute inset-0 flex h-full w-full justify-center [transform:skew(-13deg)_translateX(-100%)] group-hover/button:duration-1000 group-hover/button:[transform:skew(-13deg)_translateX(100%)]">
                      <div className="relative h-full w-8 bg-white/20" />
                    </div>
                  </button>
                </div>

                <p className="text-xs leading-relaxed text-[var(--color-text-secondary)]">
                  By signing up you agree to the{' '}
                  <Link href="#" className="text-[var(--color-text-primary)] hover:underline">
                    Terms
                  </Link>{' '}
                  and{' '}
                  <Link href="#" className="text-[var(--color-text-primary)] hover:underline">
                    Privacy Policy
                  </Link>
                  .
                </p>

                <p className="text-sm text-[var(--color-text-secondary)]">
                  Already have an account?{' '}
                  <Link
                    href="/login"
                    className="font-medium text-[var(--color-text-primary)] hover:underline"
                  >
                    Sign in
                  </Link>
                </p>
              </form>
            </div>
          </div>

          <div className="relative hidden min-h-[600px] w-1/2 overflow-hidden lg:block">
            <Image
              src="https://images.pexels.com/photos/4484078/pexels-photo-4484078.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2"
              loader={({ src }) => src}
              width={1000}
              height={1000}
              priority
              alt=""
              className="h-full min-h-[600px] w-full object-cover opacity-40"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-[var(--color-bg)] via-transparent to-transparent" />
          </div>
        </div>
      </div>
    </div>
  )
}
