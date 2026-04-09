import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import PageWrapper from '@/components/layout/PageWrapper'
import PortfolioChart from '@/components/charts/PortfolioChart'
import PnlBadge from '@/components/common/PnlBadge'
import { useAuth } from '@/auth/AuthContext'
import { getPortfolio } from '@/api/trading'
import { formatCurrency } from '@/lib/utils'

export default function PortfolioPage() {
  const { user } = useAuth()
  const homeCurrency = user?.home_currency ?? 'GBP'

  const { data: portfolio, isLoading } = useQuery({
    queryKey: ['portfolio'],
    queryFn: getPortfolio,
    staleTime: 30_000,
  })

  return (
    <PageWrapper title="Portfolio">
      <div className="space-y-6">
        {/* Summary cards */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <p className="mb-1 text-xs text-slate-500">Market value</p>
            <p className="text-lg font-semibold text-white">
              {formatCurrency(portfolio?.total_value, homeCurrency)}
            </p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <p className="mb-1 text-xs text-slate-500">Cost basis</p>
            <p className="text-lg font-semibold text-white">
              {formatCurrency(portfolio?.total_cost, homeCurrency)}
            </p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <p className="mb-1 text-xs text-slate-500">Unrealised P&L</p>
            <p className="text-lg font-semibold">
              <PnlBadge
                value={portfolio?.total_pnl}
                currency={homeCurrency}
                percent={portfolio?.pnl_percent}
              />
            </p>
          </div>
        </div>

        <PortfolioChart />

        {/* Positions table */}
        {isLoading ? (
          <div className="flex h-40 items-center justify-center">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-700 border-t-indigo-500" />
          </div>
        ) : (portfolio?.positions.length ?? 0) === 0 ? (
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-8 text-center">
            <p className="text-slate-400">No open positions. <Link to="/market" className="text-indigo-400 hover:text-indigo-300">Browse markets →</Link></p>
          </div>
        ) : (
          <div className="rounded-xl border border-slate-800 bg-slate-900">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-800 text-xs text-slate-500">
                    <th className="px-4 py-3 text-left">Asset</th>
                    <th className="px-4 py-3 text-right">Qty</th>
                    <th className="px-4 py-3 text-right">Avg cost</th>
                    <th className="px-4 py-3 text-right">Price</th>
                    <th className="px-4 py-3 text-right">Value</th>
                    <th className="px-4 py-3 text-right">Unrealised P&L</th>
                    <th className="px-4 py-3 text-right">Realised P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio?.positions.map((p) => (
                    <tr key={p.id} className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/30">
                      <td className="px-4 py-3">
                        <Link
                          to={`/market/${p.exchange_code}/${p.asset_ticker}`}
                          className="font-medium text-white hover:text-indigo-400"
                        >
                          {p.asset_ticker}
                        </Link>
                        <span className="ml-1.5 text-xs text-slate-500">{p.exchange_code}</span>
                        <p className="text-xs text-slate-500">{p.asset_name}</p>
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-slate-300">{p.quantity}</td>
                      <td className="px-4 py-3 text-right tabular-nums text-slate-300">
                        {formatCurrency(p.avg_cost_home, homeCurrency)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-slate-300">
                        {formatCurrency(p.current_price_home, homeCurrency)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-slate-300">
                        {formatCurrency(p.current_value_home, homeCurrency)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <PnlBadge value={p.unrealized_pnl_home} currency={homeCurrency} percent={p.pnl_percent} size="sm" />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <PnlBadge value={p.realized_pnl_home} currency={homeCurrency} size="sm" />
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
