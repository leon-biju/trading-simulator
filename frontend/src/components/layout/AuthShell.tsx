import type { ReactNode } from 'react'
//TODO: Use real market data
const FAKE_MOVERS = [
  { ticker: 'NVDA', name: 'NVIDIA Corp',    pct: +4.23 },
  { ticker: 'AAPL', name: 'Apple Inc',      pct: -1.87 },
  { ticker: 'BTC',  name: 'Bitcoin',        pct: +6.11 },
  { ticker: 'TSLA', name: 'Tesla Inc',      pct: -3.42 },
  { ticker: 'MSFT', name: 'Microsoft Corp', pct: +2.08 },
]

export default function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-[calc(100svh-3rem)] items-stretch">

      {/* ── Left: branding ──────────────────────────────── */}
      <div className="relative hidden lg:flex lg:flex-1 flex-col justify-between overflow-hidden border-r border-edge bg-panel px-12 py-14">
        {/* Grid overlay */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: 'linear-gradient(#E2E8F0 1px, transparent 1px), linear-gradient(90deg, #E2E8F0 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
        />
        {/* Glow */}
        <div className="pointer-events-none absolute -top-32 -left-32 h-96 w-96 rounded-full bg-brand/5 blur-3xl" />

        {/* Tagline */}
        <div className="relative space-y-8">
          <div>
            <h2 className="text-3xl font-semibold text-bright leading-tight">
              Trade smarter.<br />Learn faster.
            </h2>
            <p className="mt-3 text-sm text-dim leading-relaxed max-w-xs">
              A risk-free simulator for mastering the markets. Real dynamics, zero financial risk.
            </p>
          </div>

          {/* Market movers */}
          <div className="rounded-xl border border-edge bg-raised/60 p-4 backdrop-blur-sm max-w-xs">
            <p className="mb-3 text-[11px] uppercase tracking-widest text-faint">Market movers</p>
            <div className="space-y-2.5">
              {FAKE_MOVERS.map((m) => (
                <div key={m.ticker} className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <span className="w-12 text-xs font-semibold text-bright font-mono">{m.ticker}</span>
                    <span className="text-[11px] text-faint">{m.name}</span>
                  </div>
                  <span className={`text-xs tabular-nums font-medium font-mono ${m.pct >= 0 ? 'text-buy' : 'text-sell'}`}>
                    {m.pct >= 0 ? '+' : ''}{m.pct.toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <p className="relative text-[11px] text-faint">Simulated funds only. No real money involved.</p>
      </div>

      {/* ── Right: form ─────────────────────────────────── */}
      <div className="flex flex-1 items-center justify-center px-6 py-12 lg:px-16">
        <div className="w-full max-w-sm">
          {children}
        </div>
      </div>

    </div>
  )
}
