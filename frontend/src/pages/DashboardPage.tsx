import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import PageWrapper from '@/components/layout/PageWrapper'
import PortfolioChart from '@/components/charts/PortfolioChart'
import PnlBadge from '@/components/common/PnlBadge'
import StatusBadge from '@/components/common/StatusBadge'
import { useAuth } from '@/auth/AuthContext'
import { getPortfolio, cancelOrder, getTrades, getOrders } from '@/api/trading'
import { getWallets } from '@/api/wallets'
import { formatCurrency, formatDateShort } from '@/lib/utils'

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-edge bg-panel px-4 py-3">
      <p className="mb-1 text-[11px] uppercase tracking-wider text-faint">{label}</p>
      <div className="text-base font-semibold text-bright">{value}</div>
    </div>
  )
}

export default function DashboardPage() {
  const { user } = useAuth()
  const qc = useQueryClient()

  const { data: portfolio } = useQuery({ queryKey: ['portfolio'], queryFn: getPortfolio, staleTime: 30_000 })
  const { data: wallets }   = useQuery({ queryKey: ['wallets'],   queryFn: getWallets,   staleTime: 30_000 })
  const { data: orders }    = useQuery({ queryKey: ['orders', 1], queryFn: () => getOrders(1), staleTime: 5_000 })
  const { data: trades }    = useQuery({ queryKey: ['trades', 1], queryFn: () => getTrades(1), staleTime: 5_000 })

  const cancelMutation = useMutation({
    mutationFn: cancelOrder,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['orders'] })
      qc.invalidateQueries({ queryKey: ['wallets'] })
    },
  })

  const homeCurrency  = user?.home_currency ?? 'GBP'
  const pendingOrders = orders?.results.filter((o) => o.status === 'PENDING') ?? []
  const recentTrades  = trades?.results.slice(0, 6) ?? []
  const totalAssets   =
    portfolio && user?.total_cash
      ? (parseFloat(portfolio.total_value) + parseFloat(user.total_cash)).toFixed(2)
      : null

  return (
    <PageWrapper>
      {/* ── Stat row ──────────────────────────────────────────── */}
      <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Total assets"   value={formatCurrency(totalAssets, homeCurrency)} />
        <Stat label="Investments"    value={formatCurrency(portfolio?.total_value, homeCurrency)} />
        <Stat label="Cash"           value={formatCurrency(user?.total_cash, homeCurrency)} />
        <Stat label="Unrealised P&L" value={
          <PnlBadge value={portfolio?.total_pnl} currency={homeCurrency} percent={portfolio?.pnl_percent} />
        } />
      </div>

      {/* ── Chart + side panel ────────────────────────────────── */}
      <div className="mb-5 grid grid-cols-1 gap-4 lg:grid-cols-3" style={{ minHeight: 320 }}>
        {/* Chart */}
        <div className="rounded-lg border border-edge bg-panel p-4 lg:col-span-2 flex flex-col" style={{ minHeight: 300 }}>
          <PortfolioChart />
        </div>

        {/* Right column */}
        <div className="flex flex-col gap-4">
          {/* Wallets */}
          <div className="rounded-lg border border-edge bg-panel p-4 flex-1">
            <h2 className="mb-3 text-[11px] uppercase tracking-wider text-faint">Cash wallets</h2>
            <div className="space-y-0.5">
              {(wallets ?? []).map((w) => (
                <Link
                  key={w.currency_code}
                  to={`/wallets/${w.currency_code}`}
                  className="flex items-center justify-between rounded px-2 py-1.5 transition hover:bg-raised"
                >
                  <span className="text-xs font-medium text-dim">{w.currency_code}</span>
                  <div className="text-right">
                    <p className="text-xs tabular-nums text-bright">
                      {formatCurrency(w.available_balance, w.currency_code)}
                    </p>
                    {parseFloat(w.pending_balance) > 0 && (
                      <p className="text-[11px] text-faint">
                        {formatCurrency(w.pending_balance, w.currency_code)} reserved
                      </p>
                    )}
                  </div>
                </Link>
              ))}
              {!wallets?.length && (
                <p className="text-xs text-faint">No wallets</p>
              )}
            </div>
          </div>

          {/* Pending orders */}
          <div className="rounded-lg border border-edge bg-panel p-4 flex-1">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-[11px] uppercase tracking-wider text-faint">Pending orders</h2>
              <Link to="/portfolio?tab=orders" className="text-[11px] text-accent hover:text-accent/80">View all</Link>
            </div>
            {pendingOrders.length === 0 ? (
              <p className="text-xs text-faint">No pending orders</p>
            ) : (
              <div className="space-y-1.5">
                {pendingOrders.slice(0, 4).map((o) => (
                  <div key={o.id} className="flex items-center justify-between rounded bg-raised/50 px-2 py-1.5">
                    <div>
                      <p className="text-xs font-medium text-bright">
                        {o.asset_ticker}
                        <span className="ml-1 text-[11px] text-faint">{o.exchange_code}</span>
                      </p>
                      <p className="text-[11px] text-dim">
                        <StatusBadge value={o.side} /> {o.quantity}
                        {o.limit_price && ` @ ${o.limit_price}`}
                      </p>
                    </div>
                    <button
                      onClick={() => cancelMutation.mutate(o.id)}
                      disabled={cancelMutation.isPending}
                      className="text-[11px] text-sell hover:text-sell/80 disabled:opacity-40"
                    >
                      Cancel
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Holdings table ─────────────────────────────────────── */}
      {(portfolio?.positions.length ?? 0) > 0 && (
        <div className="mb-5 rounded-lg border border-edge bg-panel">
          <div className="flex items-center justify-between border-b border-edge px-4 py-3">
            <h2 className="text-[11px] uppercase tracking-wider text-faint">Holdings</h2>
            <Link to="/portfolio" className="text-[11px] text-accent hover:text-accent/80">Full portfolio →</Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-edge text-[11px] uppercase tracking-wider text-faint">
                  <th className="px-4 py-2.5 text-left font-medium">Asset</th>
                  <th className="px-4 py-2.5 text-right font-medium">Qty</th>
                  <th className="px-4 py-2.5 text-right font-medium">Avg cost</th>
                  <th className="px-4 py-2.5 text-right font-medium">Price</th>
                  <th className="px-4 py-2.5 text-right font-medium">P&L</th>
                </tr>
              </thead>
              <tbody>
                {portfolio?.positions.map((p) => (
                  <tr key={p.id} className="border-b border-edge/50 last:border-0 hover:bg-raised/40 transition-colors">
                    <td className="px-4 py-2.5">
                      <Link
                        to={`/market/${p.exchange_code}/${p.asset_ticker}`}
                        className="font-medium text-bright hover:text-accent transition-colors"
                      >
                        {p.asset_ticker}
                      </Link>
                      <span className="ml-1.5 text-[11px] text-faint">{p.exchange_code}</span>
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-dim text-xs">{p.quantity}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-dim text-xs">
                      {formatCurrency(p.avg_cost_home, homeCurrency)}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-dim text-xs">
                      {formatCurrency(p.current_price_home, homeCurrency)}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <PnlBadge value={p.unrealized_pnl_home} currency={homeCurrency} percent={p.pnl_percent} size="sm" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Recent trades ──────────────────────────────────────── */}
      {recentTrades.length > 0 && (
        <div className="rounded-lg border border-edge bg-panel">
          <div className="flex items-center justify-between border-b border-edge px-4 py-3">
            <h2 className="text-[11px] uppercase tracking-wider text-faint">Recent trades</h2>
            <Link to="/portfolio?tab=trades" className="text-[11px] text-accent hover:text-accent/80">View all →</Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <tbody>
                {recentTrades.map((t) => (
                  <tr key={t.id} className="border-b border-edge/40 last:border-0 hover:bg-raised/30 transition-colors">
                    <td className="px-4 py-2 text-[11px] text-faint w-32">{formatDateShort(t.executed_at)}</td>
                    <td className="px-4 py-2">
                      <span className="text-xs font-medium text-bright">{t.asset_ticker}</span>
                      <span className="ml-1 text-[11px] text-faint">{t.exchange_code}</span>
                    </td>
                    <td className="px-4 py-2"><StatusBadge value={t.side} /></td>
                    <td className="px-4 py-2 text-[11px] tabular-nums text-dim">{t.quantity}</td>
                    <td className="px-4 py-2 text-right tabular-nums text-xs text-bright">
                      {t.total_value_home
                        ? formatCurrency(t.total_value_home, homeCurrency)
                        : formatCurrency(t.total_value, t.asset_currency_code)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </PageWrapper>
  )
}
