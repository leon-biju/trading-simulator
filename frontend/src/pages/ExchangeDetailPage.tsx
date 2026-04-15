import { useState, useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search, X } from 'lucide-react'
import PageWrapper from '@/components/layout/PageWrapper'
import StatusBadge from '@/components/common/StatusBadge'
import { getExchange } from '@/api/market'
import { formatCurrency, cn } from '@/lib/utils'

export default function ExchangeDetailPage() {
  const { exchangeCode } = useParams<{ exchangeCode: string }>()
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<string | null>(null)

  const { data: exchange, isLoading } = useQuery({
    queryKey: ['exchange', exchangeCode],
    queryFn: () => getExchange(exchangeCode!),
    staleTime: 60_000,
  })

  const assetTypes = useMemo(() => {
    if (!exchange) return []
    return [...new Set(exchange.assets.map(a => a.asset_type).filter(Boolean))]
  }, [exchange])

  const query = search.trim().toLowerCase()

  const filteredAssets = useMemo(() => {
    if (!exchange) return []
    return exchange.assets.filter(asset => {
      const matchesSearch =
        !query ||
        asset.ticker.toLowerCase().includes(query) ||
        asset.name.toLowerCase().includes(query)
      const matchesType = !typeFilter || asset.asset_type === typeFilter
      return matchesSearch && matchesType
    })
  }, [exchange, query, typeFilter])

  return (
    <PageWrapper>
      {isLoading ? (
        <div className="flex h-40 items-center justify-center">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-edge border-t-brand" />
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
          <div className="mb-5 flex flex-wrap items-center gap-3">
            <h1 className="text-lg font-semibold text-bright">{exchange.name}</h1>
            <span className="text-xs text-faint font-mono">{exchange.code}</span>
            <StatusBadge value={exchange.is_open ? 'OPEN' : 'CLOSED'} />
            {!exchange.is_open && exchange.hours_until_open != null && (
              <span className="text-xs text-faint">Opens in {exchange.hours_until_open}h</span>
            )}
          </div>

          {/* Search + type filters */}
          <div className="mb-4 flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-faint pointer-events-none" />
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search by ticker or name..."
                className="w-full rounded-lg border border-edge bg-panel pl-10 pr-10 py-2 text-sm text-bright placeholder:text-faint focus:outline-none focus:border-brand/50 transition-colors"
              />
              {search && (
                <button
                  onClick={() => setSearch('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-faint hover:text-dim transition-colors"
                >
                  <X className="size-4" />
                </button>
              )}
            </div>

            {assetTypes.length > 1 && (
              <div className="flex items-center gap-1.5 flex-wrap">
                <button
                  onClick={() => setTypeFilter(null)}
                  className={cn(
                    'px-3 py-1.5 rounded border text-[11px] font-medium transition-colors',
                    !typeFilter
                      ? 'border-brand/50 bg-brand/10 text-brand'
                      : 'border-edge text-faint hover:text-dim',
                  )}
                >
                  All
                </button>
                {assetTypes.map(type => (
                  <button
                    key={type}
                    onClick={() => setTypeFilter(typeFilter === type ? null : type)}
                    className={cn(
                      'px-3 py-1.5 rounded border text-[11px] font-medium transition-colors',
                      typeFilter === type
                        ? 'border-brand/50 bg-brand/10 text-brand'
                        : 'border-edge text-faint hover:text-dim',
                    )}
                  >
                    {type}
                  </button>
                ))}
              </div>
            )}
          </div>

          {(query || typeFilter) && (
            <p className="text-xs text-faint mb-3">
              {filteredAssets.length} result{filteredAssets.length !== 1 ? 's' : ''}
              {query ? ` for "${search.trim()}"` : ''}
            </p>
          )}

          {/* Assets table */}
          <div className="rounded-lg border border-edge bg-panel overflow-hidden">
            {filteredAssets.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <p className="text-dim text-sm">No assets found</p>
                <p className="text-faint text-xs mt-1">Try adjusting your search or filters</p>
              </div>
            ) : (
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
                  {filteredAssets.map(asset => (
                    <tr
                      key={asset.ticker}
                      className="border-b border-edge/40 last:border-0 hover:bg-raised/50 transition-colors"
                    >
                      <td className="px-4 py-2.5">
                        <span className="text-sm font-semibold text-bright font-mono">{asset.ticker}</span>
                      </td>
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
                          className="inline-flex items-center rounded border border-edge px-2.5 py-1 text-[11px] text-dim transition hover:border-brand hover:text-brand"
                        >
                          Trade
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      ) : (
        <p className="text-dim">Exchange not found.</p>
      )}
    </PageWrapper>
  )
}
