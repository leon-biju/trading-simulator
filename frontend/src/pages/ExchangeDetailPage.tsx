import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import PageWrapper from '@/components/layout/PageWrapper'
import StatusBadge from '@/components/common/StatusBadge'
import { getExchange } from '@/api/market'
import { formatCurrency } from '@/lib/utils'

export default function ExchangeDetailPage() {
  const { exchangeCode } = useParams<{ exchangeCode: string }>()

  const { data: exchange, isLoading } = useQuery({
    queryKey: ['exchange', exchangeCode],
    queryFn: () => getExchange(exchangeCode!),
    staleTime: 60_000,
  })

  return (
    <PageWrapper>
      {isLoading ? (
        <div className="flex h-40 items-center justify-center">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-edge border-t-accent" />
        </div>
      ) : exchange ? (
        <div>
          {/* Breadcrumb */}
          <div className="mb-5 flex items-center gap-2 text-[11px] text-faint">
            <Link to="/market" className="hover:text-dim transition-colors">Markets</Link>
            <span>/</span>
            <span className="text-dim">{exchange.name}</span>
          </div>

          {/* Header */}
          <div className="mb-5 flex items-center gap-3">
            <h1 className="text-lg font-semibold text-bright">{exchange.name}</h1>
            <span className="text-xs text-faint">{exchange.code}</span>
            <StatusBadge value={exchange.is_open ? 'OPEN' : 'CLOSED'} />
          </div>

          {/* Assets table */}
          <div className="rounded-lg border border-edge bg-panel">
            <table className="w-full">
              <thead>
                <tr className="border-b border-edge text-[11px] uppercase tracking-wider text-faint">
                  <th className="px-4 py-3 text-left font-medium">Ticker</th>
                  <th className="px-4 py-3 text-left font-medium">Name</th>
                  <th className="px-4 py-3 text-left font-medium hidden sm:table-cell">Type</th>
                  <th className="px-4 py-3 text-right font-medium">Price</th>
                  <th className="px-4 py-3 text-right font-medium w-20"></th>
                </tr>
              </thead>
              <tbody>
                {exchange.assets.map((asset) => (
                  <tr
                    key={asset.ticker}
                    className="border-b border-edge/40 last:border-0 hover:bg-raised/50 transition-colors"
                  >
                    <td className="px-4 py-2.5 font-semibold text-bright text-sm">{asset.ticker}</td>
                    <td className="px-4 py-2.5 text-xs text-dim">{asset.name}</td>
                    <td className="px-4 py-2.5 hidden sm:table-cell">
                      <span className="text-[11px] text-faint">{asset.asset_type}</span>
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-xs font-medium text-bright">
                      {asset.current_price
                        ? formatCurrency(asset.current_price, asset.currency_code)
                        : <span className="text-faint">—</span>}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <Link
                        to={`/market/${exchange.code}/${asset.ticker}`}
                        className="inline-flex items-center rounded border border-edge px-2.5 py-1 text-[11px] text-dim transition hover:border-accent hover:text-accent"
                      >
                        Trade
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <p className="text-dim">Exchange not found.</p>
      )}
    </PageWrapper>
  )
}
