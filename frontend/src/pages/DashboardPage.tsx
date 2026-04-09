import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import PageWrapper from '@/components/layout/PageWrapper'
import PortfolioChart from '@/components/charts/PortfolioChart'
import PnlBadge from '@/components/common/PnlBadge'
import StatusBadge from '@/components/common/StatusBadge'
import { useAuth } from '@/auth/AuthContext'
import { getPortfolio, cancelOrder, getTrades, getOrders } from '@/api/trading'
import { getWallets } from '@/api/wallets'
import { formatCurrency, formatDate } from '@/lib/utils'

export default function DashboardPage() {
  const { user } = useAuth()
  const qc = useQueryClient()

  const { data: portfolio } = useQuery({
    queryKey: ['portfolio'],
    queryFn: getPortfolio,
    staleTime: 30_000,
  })

  const { data: wallets } = useQuery({
    queryKey: ['wallets'],
    queryFn: getWallets,
    staleTime: 30_000,
  })

  const { data: orders } = useQuery({
    queryKey: ['orders', 1],
    queryFn: () => getOrders(1),
    staleTime: 5_000,
  })

  const { data: trades } = useQuery({
    queryKey: ['trades', 1],
    queryFn: () => getTrades(1),
    staleTime: 5_000,
  })

  const cancelMutation = useMutation({
    mutationFn: cancelOrder,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['orders'] })
      qc.invalidateQueries({ queryKey: ['wallets'] })
    },
  })

  const homeCurrency = user?.home_currency ?? 'GBP'
  const pendingOrders = orders?.results.filter((o) => o.status === 'PENDING') ?? []
  const recentTrades = trades?.results.slice(0, 5) ?? []

  const totalAssets =
    portfolio && user?.total_cash
      ? (parseFloat(portfolio.total_value) + parseFloat(user.total_cash)).toFixed(2)
      : null

  return (
    <PageWrapper>
      <div className="space-y-6">
        {/* Summary cards */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: 'Total assets', value: formatCurrency(totalAssets, homeCurrency) },
            { label: 'Investments', value: formatCurrency(portfolio?.total_value, homeCurrency) },
            { label: 'Cash', value: formatCurrency(user?.total_cash, homeCurrency) },
            {
              label: 'Unrealised P&L',
              value: (
                <PnlBadge
                  value={portfolio?.total_pnl}
                  currency={homeCurrency}
                  percent={portfolio?.pnl_percent}
                />
              ),
            },
          ].map(({ label, value }) => (
            <div key={label} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <p className="mb-1 text-xs text-slate-500">{label}</p>
              <p className="text-lg font-semibold text-white">{value}</p>
            </div>
          ))}
        </div>

        {/* Chart */}
        <PortfolioChart />

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Wallets */}
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <h2 className="mb-3 text-sm font-medium text-slate-300">Cash wallets</h2>
            <div className="space-y-1">
              {(wallets ?? []).map((w) => (
                <Link
                  key={w.currency_code}
                  to={`/wallets/${w.currency_code}`}
                  className="flex items-center justify-between rounded-lg px-3 py-2 transition hover:bg-slate-800"
                >
                  <span className="text-sm font-medium text-slate-200">{w.currency_code}</span>
                  <div className="text-right">
                    <p className="text-sm tabular-nums text-white">
                      {formatCurrency(w.available_balance, w.currency_code)}
                    </p>
                    {parseFloat(w.pending_balance) > 0 && (
                      <p className="text-xs text-slate-500">
                        {formatCurrency(w.pending_balance, w.currency_code)} reserved
                      </p>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          </div>

          {/* Pending orders */}
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-medium text-slate-300">Pending orders</h2>
              <Link to="/orders" className="text-xs text-indigo-400 hover:text-indigo-300">View all</Link>
            </div>
            {pendingOrders.length === 0 ? (
              <p className="text-sm text-slate-500">No pending orders</p>
            ) : (
              <div className="space-y-2">
                {pendingOrders.slice(0, 5).map((o) => (
                  <div key={o.id} className="flex items-center justify-between rounded-lg bg-slate-800/50 px-3 py-2">
                    <div>
                      <p className="text-sm font-medium text-white">
                        {o.asset_ticker}
                        <span className="ml-1.5 text-xs text-slate-400">{o.exchange_code}</span>
                      </p>
                      <p className="text-xs text-slate-400">
                        <StatusBadge value={o.side} /> {o.quantity}
                        {o.limit_price && ` @ ${o.limit_price}`}
                      </p>
                    </div>
                    <button
                      onClick={() => cancelMutation.mutate(o.id)}
                      disabled={cancelMutation.isPending}
                      className="text-xs text-red-400 hover:text-red-300 disabled:opacity-50"
                    >
                      Cancel
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent trades */}
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-medium text-slate-300">Recent trades</h2>
              <Link to="/trades" className="text-xs text-indigo-400 hover:text-indigo-300">View all</Link>
            </div>
            {recentTrades.length === 0 ? (
              <p className="text-sm text-slate-500">No trades yet</p>
            ) : (
              <div className="space-y-2">
                {recentTrades.map((t) => (
                  <div key={t.id} className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-white">
                        <StatusBadge value={t.side} />
                        <span className="ml-1.5">{t.quantity} {t.asset_ticker}</span>
                      </p>
                      <p className="text-xs text-slate-500">{formatDate(t.executed_at)}</p>
                    </div>
                    <p className="text-sm tabular-nums text-slate-300">
                      {t.total_value_home
                        ? formatCurrency(t.total_value_home, homeCurrency)
                        : formatCurrency(t.total_value, t.asset_currency_code)}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Holdings table */}
        {(portfolio?.positions.length ?? 0) > 0 && (
          <div className="rounded-xl border border-slate-800 bg-slate-900">
            <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
              <h2 className="text-sm font-medium text-slate-300">Holdings</h2>
              <Link to="/portfolio" className="text-xs text-indigo-400 hover:text-indigo-300">Full portfolio</Link>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-800 text-xs text-slate-500">
                    <th className="px-4 py-2 text-left">Asset</th>
                    <th className="px-4 py-2 text-right">Qty</th>
                    <th className="px-4 py-2 text-right">Avg cost</th>
                    <th className="px-4 py-2 text-right">Price</th>
                    <th className="px-4 py-2 text-right">P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio?.positions.map((p) => (
                    <tr key={p.id} className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/30">
                      <td className="px-4 py-2.5">
                        <Link
                          to={`/market/${p.exchange_code}/${p.asset_ticker}`}
                          className="font-medium text-white hover:text-indigo-400"
                        >
                          {p.asset_ticker}
                        </Link>
                        <span className="ml-1.5 text-xs text-slate-500">{p.exchange_code}</span>
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-slate-300">{p.quantity}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-slate-300">
                        {formatCurrency(p.avg_cost_home, homeCurrency)}
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-slate-300">
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
      </div>
    </PageWrapper>
  )
}
