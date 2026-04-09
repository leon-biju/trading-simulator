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
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-700 border-t-indigo-500" />
        </div>
      ) : exchange ? (
        <div>
          {/* Breadcrumb */}
          <div className="mb-4 flex items-center gap-2 text-xs text-slate-500">
            <Link to="/market" className="hover:text-slate-300">Markets</Link>
            <span>/</span>
            <span className="text-slate-300">{exchange.name}</span>
          </div>

          {/* Header */}
          <div className="mb-6 flex items-center gap-3">
            <h1 className="text-xl font-semibold text-white">{exchange.name}</h1>
            <span className="text-sm text-slate-500">{exchange.code}</span>
            <StatusBadge value={exchange.is_open ? 'OPEN' : 'CLOSED'} />
          </div>

          {/* Assets table */}
          <div className="rounded-xl border border-slate-800 bg-slate-900">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-800 text-xs text-slate-500">
                    <th className="px-4 py-3 text-left">Ticker</th>
                    <th className="px-4 py-3 text-left">Name</th>
                    <th className="px-4 py-3 text-left">Type</th>
                    <th className="px-4 py-3 text-right">Price</th>
                    <th className="px-4 py-3 text-right"></th>
                  </tr>
                </thead>
                <tbody>
                  {exchange.assets.map((asset) => (
                    <tr
                      key={asset.ticker}
                      className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/30"
                    >
                      <td className="px-4 py-3 font-medium text-white">{asset.ticker}</td>
                      <td className="px-4 py-3 text-slate-400">{asset.name}</td>
                      <td className="px-4 py-3">
                        <span className="text-xs text-slate-500">{asset.asset_type}</span>
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-slate-300">
                        {asset.current_price
                          ? formatCurrency(asset.current_price, asset.currency_code)
                          : '—'}
                      </td>
                      <td className="px-4 py-3 text-right">
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
          </div>
        </div>
      ) : (
        <p className="text-slate-400">Exchange not found.</p>
      )}
    </PageWrapper>
  )
}
