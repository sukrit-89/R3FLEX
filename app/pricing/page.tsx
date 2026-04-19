import Link from "next/link"
import { Check, Minus } from "lucide-react"
import { SiteHeader } from "@/components/landing/site-header"
import { SiteFooter } from "@/components/landing/site-footer"
import { cn } from "@/lib/utils"

type Tier = {
  name: string
  tagline: string
  price: string
  unit: string
  cta: { label: string; href: string }
  highlight?: boolean
  features: string[]
}

const tiers: Tier[] = [
  {
    name: "Starter",
    tagline: "For individual operators getting signals off the ground.",
    price: "$0",
    unit: "/ forever",
    cta: { label: "Start free", href: "/signup" },
    features: [
      "Up to 3 detection nodes",
      "10,000 events / month",
      "7-day event retention",
      "Community support",
      "Basic anomaly alerts",
    ],
  },
  {
    name: "Team",
    tagline: "For ops teams who need shared visibility and fast response.",
    price: "$49",
    unit: "/ seat / month",
    cta: { label: "Start 14-day trial", href: "/signup" },
    highlight: true,
    features: [
      "Unlimited detection nodes",
      "2M events / month included",
      "90-day event retention",
      "Role-based access control",
      "Detection Engine + custom rules",
      "Priority email & chat support",
      "Slack & webhook integrations",
    ],
  },
  {
    name: "Enterprise",
    tagline: "For the mission-critical networks your business runs on.",
    price: "Custom",
    unit: "annual agreement",
    cta: { label: "Talk to sales", href: "#" },
    features: [
      "Unlimited events & retention",
      "Dedicated detection cluster",
      "SOC 2 Type II + HIPAA + FedRAMP",
      "SSO, SCIM, audit log streaming",
      "Dedicated Solutions Architect",
      "99.99% uptime SLA",
      "On-prem & air-gapped deployments",
    ],
  },
]

const compareRows: { label: string; values: [string | boolean, string | boolean, string | boolean] }[] = [
  { label: "Detection nodes", values: ["3", "Unlimited", "Unlimited"] },
  { label: "Events per month", values: ["10K", "2M", "Custom"] },
  { label: "Event retention", values: ["7 days", "90 days", "Custom"] },
  { label: "Custom rules engine", values: [false, true, true] },
  { label: "Role-based access", values: [false, true, true] },
  { label: "SSO / SCIM", values: [false, false, true] },
  { label: "Audit log streaming", values: [false, false, true] },
  { label: "Dedicated Solutions Architect", values: [false, false, true] },
  { label: "Uptime SLA", values: ["—", "99.9%", "99.99%"] },
  { label: "Support", values: ["Community", "Priority", "24/7 + pager"] },
]

const faqs = [
  {
    q: "How does billing work?",
    a: "Team plans are billed monthly per seat. Annual commitments save 20%. You can change plans or cancel anytime from your workspace settings.",
  },
  {
    q: "What counts as an event?",
    a: "An event is any discrete signal ingested by GlobalTracker — a customs update, RFID scan, route telemetry ping, or API-reported state change.",
  },
  {
    q: "Do you offer non-profit or academic pricing?",
    a: "Yes. We offer 70% off Team plans for qualifying non-profits and research institutions. Contact our sales team to apply.",
  },
  {
    q: "Can I self-host GlobalTracker?",
    a: "Enterprise customers can deploy on-prem or in an air-gapped environment. Reach out and we&apos;ll walk you through the deployment options.",
  },
]

export default function PricingPage() {
  return (
    <main className="relative min-h-screen bg-background text-foreground overflow-x-hidden">
      <SiteHeader />

      {/* Grid backdrop */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.12]"
        style={{
          backgroundImage:
            "linear-gradient(to right, #31374A 1px, transparent 1px), linear-gradient(to bottom, #31374A 1px, transparent 1px)",
          backgroundSize: "64px 64px",
          maskImage: "linear-gradient(to bottom, black, transparent 70%)",
          WebkitMaskImage: "linear-gradient(to bottom, black, transparent 70%)",
        }}
      />

      {/* Hero */}
      <section className="relative pt-40 pb-16 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl text-center">
          <div className="inline-flex items-center gap-2 mb-6 px-3 py-1 rounded-full border border-border bg-card/60 backdrop-blur-sm text-xs font-mono uppercase tracking-[0.2em] text-muted-foreground">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            Pricing
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-semibold tracking-tight leading-[1.05] text-balance">
            Plans that scale with your <span className="text-primary">network</span>.
          </h1>
          <p className="mt-6 text-lg text-muted-foreground text-pretty max-w-2xl mx-auto leading-relaxed">
            Start free. Upgrade when your operation outgrows a dashboard — and never worry about
            being rate-limited during an incident again.
          </p>
        </div>
      </section>

      {/* Pricing cards */}
      <section className="relative px-4 sm:px-6 lg:px-8 pb-24">
        <div className="mx-auto max-w-7xl grid gap-6 md:grid-cols-3">
          {tiers.map((tier) => (
            <div
              key={tier.name}
              className={cn(
                "relative rounded-2xl border bg-card/60 backdrop-blur-xl p-8 flex flex-col transition-all",
                tier.highlight
                  ? "border-primary/60 shadow-[0_0_40px_-10px_rgba(0,196,204,0.4)]"
                  : "border-border hover:border-primary/30",
              )}
            >
              {tier.highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-primary text-primary-foreground text-[10px] font-mono uppercase tracking-[0.2em]">
                  Most Popular
                </div>
              )}

              <div className="mb-6">
                <h3 className="text-xl font-semibold">{tier.name}</h3>
                <p className="mt-2 text-sm text-muted-foreground text-pretty">{tier.tagline}</p>
              </div>

              <div className="mb-6">
                <div className="flex items-baseline gap-2">
                  <span className="text-5xl font-semibold tracking-tight">{tier.price}</span>
                  <span className="text-sm text-muted-foreground">{tier.unit}</span>
                </div>
              </div>

              <Link
                href={tier.cta.href}
                className={cn(
                  "mb-8 inline-flex items-center justify-center h-11 rounded-lg px-4 font-medium text-sm transition-colors",
                  tier.highlight
                    ? "bg-primary text-primary-foreground hover:bg-primary/90"
                    : "border border-border bg-card hover:border-primary/40 hover:bg-card/80 text-foreground",
                )}
              >
                {tier.cta.label}
              </Link>

              <ul className="space-y-3 text-sm">
                {tier.features.map((f) => (
                  <li key={f} className="flex items-start gap-3">
                    <span className="mt-0.5 grid place-items-center w-5 h-5 rounded-full bg-primary/15 text-primary flex-shrink-0">
                      <Check className="w-3 h-3" />
                    </span>
                    <span className="text-foreground/90">{f}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* Compare table */}
      <section className="relative px-4 sm:px-6 lg:px-8 pb-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-10 text-center">
            <div className="inline-flex items-center gap-2 mb-4 px-3 py-1 rounded-full border border-border bg-card/60 backdrop-blur-sm text-xs font-mono uppercase tracking-[0.2em] text-muted-foreground">
              Compare
            </div>
            <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-balance">
              Every feature, side by side.
            </h2>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-border bg-card/40 backdrop-blur-xl">
            <table className="w-full text-sm min-w-[640px]">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left font-medium text-muted-foreground px-6 py-4 w-2/5">
                    Feature
                  </th>
                  {tiers.map((t) => (
                    <th
                      key={t.name}
                      className={cn(
                        "text-left font-medium px-6 py-4",
                        t.highlight ? "text-primary" : "text-foreground",
                      )}
                    >
                      {t.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {compareRows.map((row, i) => (
                  <tr
                    key={row.label}
                    className={cn(
                      "border-b border-border/60 last:border-b-0",
                      i % 2 === 1 && "bg-muted/20",
                    )}
                  >
                    <td className="px-6 py-4 text-foreground/90">{row.label}</td>
                    {row.values.map((v, vi) => (
                      <td key={vi} className="px-6 py-4">
                        {typeof v === "boolean" ? (
                          v ? (
                            <Check className="w-4 h-4 text-primary" />
                          ) : (
                            <Minus className="w-4 h-4 text-muted-foreground/40" />
                          )
                        ) : (
                          <span className="text-foreground/90">{v}</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="relative px-4 sm:px-6 lg:px-8 pb-24">
        <div className="mx-auto max-w-3xl">
          <div className="mb-10 text-center">
            <div className="inline-flex items-center gap-2 mb-4 px-3 py-1 rounded-full border border-border bg-card/60 backdrop-blur-sm text-xs font-mono uppercase tracking-[0.2em] text-muted-foreground">
              FAQ
            </div>
            <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-balance">
              Questions, answered.
            </h2>
          </div>

          <div className="space-y-3">
            {faqs.map((faq) => (
              <details
                key={faq.q}
                className="group rounded-xl border border-border bg-card/60 backdrop-blur-sm open:border-primary/40 transition-colors"
              >
                <summary className="cursor-pointer list-none flex items-center justify-between gap-4 px-5 py-4 font-medium text-foreground">
                  <span className="text-balance">{faq.q}</span>
                  <span className="grid place-items-center w-6 h-6 rounded-full border border-border text-muted-foreground group-open:rotate-45 group-open:border-primary/40 group-open:text-primary transition-all">
                    <span className="text-lg leading-none">+</span>
                  </span>
                </summary>
                <div className="px-5 pb-5 text-sm text-muted-foreground leading-relaxed">
                  {faq.a}
                </div>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* CTA strip */}
      <section className="relative px-4 sm:px-6 lg:px-8 pb-24">
        <div className="mx-auto max-w-5xl rounded-3xl border border-border bg-gradient-to-br from-card via-card to-muted/40 p-10 md:p-14 text-center">
          <h3 className="text-3xl sm:text-4xl font-semibold tracking-tight text-balance">
            Ready to see every signal?
          </h3>
          <p className="mt-4 text-muted-foreground max-w-xl mx-auto">
            Spin up a workspace in minutes — no credit card required. Keep what you build.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/signup"
              className="inline-flex items-center justify-center h-11 px-6 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 transition-colors"
            >
              Start free trial
            </Link>
            <Link
              href="#"
              className="inline-flex items-center justify-center h-11 px-6 rounded-lg border border-border bg-transparent text-foreground font-medium hover:border-primary/40 transition-colors"
            >
              Book a demo
            </Link>
          </div>
        </div>
      </section>

      <SiteFooter />
    </main>
  )
}
