import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

const FAKE_MOVERS = [
  { ticker: 'NVDA', name: 'NVIDIA Corp',    pct: +4.23 },
  { ticker: 'AAPL', name: 'Apple Inc',      pct: -1.87 },
  { ticker: 'BTC',  name: 'Bitcoin',        pct: +6.11 },
  { ticker: 'TSLA', name: 'Tesla Inc',      pct: -3.42 },
  { ticker: 'MSFT', name: 'Microsoft Corp', pct: +2.08 },
]

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-base">
      {/* ── Left branding panel ───────────────────────────── */}
      <div className="hidden lg:flex lg:w-[42%] flex-col justify-between bg-panel border-r border-edge px-10 py-10 relative overflow-hidden">
        {/* Subtle grid overlay */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: 'linear-gradient(#E2E8F0 1px, transparent 1px), linear-gradient(90deg, #E2E8F0 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
        />
        {/* Glow */}
        <div className="pointer-events-none absolute -top-32 -left-32 h-96 w-96 rounded-full bg-brand/5 blur-3xl" />

        {/* Logo */}
        <div className="relative flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-brand text-sm font-bold text-base leading-none select-none">
            TS
          </div>
          <span className="text-base font-semibold tracking-tight text-bright">
            Trade<span className="text-brand">Sim</span>
          </span>
        </div>

        {/* Tagline + market movers */}
        <div className="relative space-y-8">
          <div>
            <h2 className="text-3xl font-semibold text-bright leading-tight">
              Trade smarter.<br />Learn faster.
            </h2>
            <p className="mt-3 text-sm text-dim leading-relaxed max-w-xs">
              A risk-free simulator for mastering the markets. Real dynamics, zero financial risk.
            </p>
          </div>

          {/* Fake market movers */}
          <div className="rounded-xl border border-edge bg-raised/60 p-4 backdrop-blur-sm">
            <p className="mb-3 text-[11px] uppercase tracking-widest text-faint">Market movers</p>
            <div className="space-y-2.5">
              {FAKE_MOVERS.map((m) => (
                <div key={m.ticker} className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <span className="w-12 text-xs font-semibold text-bright font-mono">{m.ticker}</span>
                    <span className="text-[11px] text-faint">{m.name}</span>
                  </div>
                  <span
                    className={`text-xs tabular-nums font-medium font-mono ${
                      m.pct >= 0 ? 'text-buy' : 'text-sell'
                    }`}
                  >
                    {m.pct >= 0 ? '+' : ''}{m.pct.toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <p className="relative text-[11px] text-faint">
          Simulated funds only. No real money involved.
        </p>
      </div>

      {/* ── Right form panel ──────────────────────────────── */}
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 lg:px-16">
        {/* Mobile-only logo */}
        <Link to="/" className="mb-8 flex items-center gap-2 lg:hidden">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-brand text-xs font-bold text-base leading-none">
            TS
          </div>
          <span className="text-sm font-semibold tracking-tight text-bright">
            Trade<span className="text-brand">Sim</span>
          </span>
        </Link>

        <div className="w-full max-w-sm">
          {children}
        </div>
      </div>
    </div>
  )
}
