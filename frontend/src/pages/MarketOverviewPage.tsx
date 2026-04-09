import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import PageWrapper from '@/components/layout/PageWrapper'
import StatusBadge from '@/components/common/StatusBadge'
import { getExchanges } from '@/api/market'
import { formatCurrency } from '@/lib/utils'

export default function MarketOverviewPage() {
  const { data: exchanges, isLoading } = useQuery({
    queryKey: ['exchanges'],
    queryFn: getExchanges,
    staleTime: 5 * 60_000,
  })

  return (
    <PageWrapper title="Markets">
      {isLoading ? (
        <div className="flex h-40 items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-700 border-t-indigo-500" />
        </div>
      ) : (
        <div className="space-y-6">
          {(exchanges ?? []).map((exchange) => (
            <div key={exchange.code} className="rounded-xl border border-slate-800 bg-slate-900">
              {/* Exchange header */}
              <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
                <div className="flex items-center gap-3">
                  <Link
                    to={`/market/${exchange.code}`}
                    className="font-medium text-white hover:text-indigo-400"
                  >
                    {exchange.name}
                  </Link>
                  <span className="text-xs text-slate-500">{exchange.code}</span>
                  <StatusBadge value={exchange.is_open ? 'OPEN' : 'CLOSED'} />
                </div>
                <div className="text-right text-xs text-slate-500">
                  {exchange.is_open
                    ? `${exchange.open_time} – ${exchange.close_time}`
                    : exchange.hours_until_open != null
                      ? `Opens in ${exchange.hours_until_open}h`
                      : 'Closed'}
                </div>
              </div>

              {/* Asset rows */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <tbody>
                    {exchange.assets.slice(0, 10).map((asset) => (
                      <tr
                        key={asset.ticker}
                        className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/30"
                      >
                        <td className="px-4 py-2.5">
                          <Link
                            to={`/market/${exchange.code}/${asset.ticker}`}
                            className="font-medium text-white hover:text-indigo-400"
                          >
                            {asset.ticker}
                          </Link>
                          <span className="ml-2 text-xs text-slate-500">{asset.name}</span>
                        </td>
                        <td className="px-4 py-2.5 text-right tabular-nums text-slate-300">
                          {asset.current_price
                            ? formatCurrency(asset.current_price, asset.currency_code)
                            : '—'}
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          <Link
                            to={`/market/${exchange.code}/${asset.ticker}`}
                            className="rounded-lg border border-slate-700 px-2.5 py-1 text-xs text-slate-400 transition hover:border-indigo-500 hover:text-white"
                          >
                            Trade
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {exchange.asset_count > 10 && (
                <div className="border-t border-slate-800 px-4 py-2 text-center">
                  <Link
                    to={`/market/${exchange.code}`}
                    className="text-xs text-indigo-400 hover:text-indigo-300"
                  >
                    View all {exchange.asset_count} assets →
                  </Link>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </PageWrapper>
  )
}
