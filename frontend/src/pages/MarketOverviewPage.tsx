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
    <PageWrapper>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-lg font-semibold text-bright">Markets</h1>
      </div>

      {isLoading ? (
        <div className="flex h-40 items-center justify-center">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-edge border-t-accent" />
        </div>
      ) : (
        <div className="space-y-4">
          {(exchanges ?? []).map((exchange) => (
            <div key={exchange.code} className="rounded-lg border border-edge bg-panel overflow-hidden">
              {/* Exchange header */}
              <div className="flex items-center justify-between border-b border-edge px-4 py-3">
                <div className="flex items-center gap-3">
                  <Link
                    to={`/market/${exchange.code}`}
                    className="text-sm font-semibold text-bright hover:text-brand transition-colors"
                  >
                    {exchange.name}
                  </Link>
                  <span className="text-[11px] text-faint">{exchange.code}</span>
                  <StatusBadge value={exchange.is_open ? 'OPEN' : 'CLOSED'} />
                </div>
                <span className="text-[11px] text-faint">
                  {exchange.is_open
                    ? `${exchange.open_time}–${exchange.close_time}`
                    : exchange.hours_until_open != null
                      ? `Opens in ${exchange.hours_until_open}h`
                      : 'Closed'}
                </span>
              </div>

              {/* Asset table */}
              <table className="w-full">
                <thead>
                  <tr className="border-b border-edge/60 text-[11px] uppercase tracking-wider text-faint">
                    <th className="px-4 py-2 text-left font-medium">Ticker</th>
                    <th className="px-4 py-2 text-left font-medium hidden sm:table-cell">Name</th>
                    <th className="px-4 py-2 text-right font-medium">Price</th>
                    <th className="px-4 py-2 text-right font-medium w-20"></th>
                  </tr>
                </thead>
                <tbody>
                  {exchange.assets.slice(0, 10).map((asset) => (
                    <tr
                      key={asset.ticker}
                      className="border-b border-edge/30 last:border-0 hover:bg-raised/50 transition-colors"
                    >
                      <td className="px-4 py-2.5">
                        <Link
                          to={`/market/${exchange.code}/${asset.ticker}`}
                          className="text-sm font-semibold text-bright hover:text-brand transition-colors"
                        >
                          {asset.ticker}
                        </Link>
                      </td>
                      <td className="px-4 py-2.5 hidden sm:table-cell">
                        <span className="text-xs text-dim">{asset.name}</span>
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-xs font-medium text-bright">
                        {asset.current_price
                          ? formatCurrency(asset.current_price, asset.currency_code)
                          : <span className="text-faint">—</span>}
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <Link
                          to={`/market/${exchange.code}/${asset.ticker}`}
                          className="inline-flex items-center rounded border border-edge px-2.5 py-1 text-[11px] text-dim transition hover:border-brand hover:text-brand"
                        >
                          Trade
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {exchange.asset_count > 10 && (
                <div className="border-t border-edge/40 px-4 py-2.5">
                  <Link
                    to={`/market/${exchange.code}`}
                    className="text-[11px] text-brand hover:text-brand/80"
                  >
                    View all {exchange.asset_count} assets on {exchange.name} →
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
