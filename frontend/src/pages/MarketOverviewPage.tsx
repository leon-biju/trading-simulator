import { useState, useMemo, useRef, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search, X, ChevronRight } from 'lucide-react'
import PageWrapper from '@/components/layout/PageWrapper'
import StatusBadge from '@/components/common/StatusBadge'
import { getExchanges, getMarketMovers } from '@/api/market'
import { formatCurrency } from '@/lib/utils'
import { useAuth } from '@/auth/AuthContext'
import { useRecentlyViewed } from '@/hooks/useRecentlyViewed'
import { useWatchlist } from '@/hooks/useWatchlist'

type MoversTab = 'gainers' | 'losers'

export default function MarketOverviewPage() {
  const [search, setSearch] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [dropdownIndex, setDropdownIndex] = useState(-1)
  const [moversTab, setMoversTab] = useState<MoversTab>('gainers')

  const searchRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const { recent } = useRecentlyViewed()
  const { watchlist } = useWatchlist()

  const { data: exchanges, isLoading } = useQuery({
    queryKey: ['exchanges'],
    queryFn: getExchanges,
    staleTime: 5 * 60_000,
  })

  const { data: movers, isLoading: moversLoading } = useQuery({
    queryKey: ['market-movers', moversTab],
    queryFn: () => getMarketMovers(moversTab, 10),
    staleTime: 30_000,
    refetchInterval: 30_000,
  })

  useEffect(() => {
    searchRef.current?.focus()
  }, [])

  const query = search.trim().toLowerCase()

  const allAssets = useMemo(() => {
    if (!exchanges) return []
    return exchanges.flatMap(exchange =>
      exchange.assets.map(asset => ({ ...asset, exchangeCode: exchange.code })),
    )
  }, [exchanges])

  const typeaheadResults = useMemo(() => {
    if (!query) return []
    return allAssets
      .filter(
        a =>
          a.ticker.toLowerCase().includes(query) ||
          a.name.toLowerCase().includes(query),
      )
      .slice(0, 8)
  }, [query, allAssets])

  const typeaheadTotal = useMemo(() => {
    if (!query) return 0
    return allAssets.filter(
      a =>
        a.ticker.toLowerCase().includes(query) ||
        a.name.toLowerCase().includes(query),
    ).length
  }, [query, allAssets])

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!showDropdown || typeaheadResults.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setDropdownIndex(i => Math.min(i + 1, typeaheadResults.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setDropdownIndex(i => Math.max(i - 1, -1))
    } else if (e.key === 'Enter' && dropdownIndex >= 0) {
      e.preventDefault()
      const asset = typeaheadResults[dropdownIndex]
      navigate(`/market/${asset.exchangeCode}/${asset.ticker}`)
      setSearch('')
      setShowDropdown(false)
    } else if (e.key === 'Escape') {
      setShowDropdown(false)
    }
  }

  // ─── inline tab helper ─────────────────────────────────────────────────────

  function tabCls(active: boolean) {
    return `text-xs font-medium transition-colors ${active ? 'text-bright' : 'text-faint hover:text-dim'}`
  }

  // ─── render ────────────────────────────────────────────────────────────────

  return (
    <PageWrapper>

      {/* ── 1. Search ─────────────────────────────────────────────────── */}
      <div className="mb-8">
        <h1 className="text-lg font-semibold text-bright mb-4">Markets</h1>

        <div className="relative">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 size-4 text-faint pointer-events-none" />
          <input
            ref={searchRef}
            type="text"
            value={search}
            onChange={e => {
              setSearch(e.target.value)
              setShowDropdown(true)
              setDropdownIndex(-1)
            }}
            onFocus={() => query && setShowDropdown(true)}
            onBlur={() => setTimeout(() => setShowDropdown(false), 150)}
            onKeyDown={handleKeyDown}
            placeholder="Search ticker or company name…"
            className="w-full rounded-lg border border-edge bg-panel pl-10 pr-10 py-3 text-sm text-bright placeholder:text-faint focus:outline-none focus:border-brand/50 transition-colors"
          />
          {search && (
            <button
              onMouseDown={e => e.preventDefault()}
              onClick={() => { setSearch(''); setShowDropdown(false); searchRef.current?.focus() }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-faint hover:text-dim transition-colors"
            >
              <X className="size-4" />
            </button>
          )}

          {/* Typeahead dropdown */}
          {showDropdown && query && (
            <div className="absolute top-full left-0 right-0 mt-1.5 rounded-lg border border-edge bg-panel shadow-2xl z-50 overflow-hidden">
              {typeaheadResults.length === 0 ? (
                <div className="px-4 py-3 text-sm text-faint">
                  No results for &ldquo;{search.trim()}&rdquo;
                </div>
              ) : (
                <>
                  {typeaheadResults.map((asset, i) => (
                    <Link
                      key={`${asset.exchangeCode}-${asset.ticker}`}
                      to={`/market/${asset.exchangeCode}/${asset.ticker}`}
                      onMouseEnter={() => setDropdownIndex(i)}
                      onClick={() => { setSearch(''); setShowDropdown(false) }}
                      className={`flex items-center gap-3 px-4 py-2.5 transition-colors ${
                        dropdownIndex === i ? 'bg-raised' : 'hover:bg-raised/50'
                      }`}
                    >
                      <span className="w-20 shrink-0 font-mono text-sm font-semibold text-bright">
                        {asset.ticker}
                      </span>
                      <span className="flex-1 text-xs text-dim truncate">{asset.name}</span>
                      <span className="text-[11px] text-faint font-mono border border-edge/60 rounded px-1.5 py-0.5">
                        {asset.exchangeCode}
                      </span>
                      <span className="w-20 text-right text-xs tabular-nums font-medium text-bright">
                        {asset.current_price
                          ? formatCurrency(asset.current_price, asset.currency_code)
                          : <span className="text-faint">—</span>}
                      </span>
                    </Link>
                  ))}
                  {typeaheadTotal > 8 && (
                    <div className="border-t border-edge/40 px-4 py-2 text-center text-[11px] text-faint">
                      Showing 8 of {typeaheadTotal} results
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="flex h-40 items-center justify-center">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-edge border-t-brand" />
        </div>
      ) : (
        <div className="space-y-9">

          {/* ── 2. Recently Viewed ──────────────────────────────────── */}
          <section>
            <span className="text-[11px] uppercase tracking-wider text-faint block mb-2.5">
              Recently Viewed
            </span>
            {recent.length === 0 ? (
              <p className="text-xs text-faint py-1">Visit an asset to build your history.</p>
            ) : (
              <div className="flex items-center overflow-x-auto">
                {recent.map((item, i) => (
                  <div key={`${item.exchangeCode}-${item.ticker}`} className="flex items-center shrink-0">
                    {i > 0 && (
                      <span className="px-3 text-faint/30 select-none text-sm">·</span>
                    )}
                    <Link
                      to={`/market/${item.exchangeCode}/${item.ticker}`}
                      className="group flex items-center gap-2 py-1"
                    >
                      <span className="font-mono text-sm font-semibold text-bright group-hover:text-brand transition-colors">
                        {item.ticker}
                      </span>
                      {item.price && (
                        <span className="text-xs tabular-nums text-dim">
                          {formatCurrency(item.price, item.currency)}
                        </span>
                      )}
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* ── 3. Market Movers + Watchlist ────────────────────────── */}
          <div className="flex flex-col md:flex-row md:items-start gap-4">

            {/* Movers */}
            <section className="flex-1 min-w-0 rounded-md border border-edge/30 px-4 py-3">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-semibold text-bright">Market Movers</span>
                <div className="flex items-center gap-4">
                  {(['gainers', 'losers'] as MoversTab[]).map(tab => (
                    <button
                      key={tab}
                      onClick={() => setMoversTab(tab)}
                      className={tabCls(moversTab === tab)}
                    >
                      {tab === 'gainers' ? 'Top Gainers' : 'Top Losers'}
                    </button>
                  ))}
                </div>
              </div>

              <table className="w-full">
                <thead>
                  <tr className="border-b border-edge/30 text-[11px] uppercase tracking-wider text-faint">
                    <th className="pb-2 pr-4 text-left font-medium w-6 hidden sm:table-cell">#</th>
                    <th className="pb-2 pr-4 text-left font-medium w-20">Ticker</th>
                    <th className="pb-2 pr-4 text-left font-medium">Name</th>
                    <th className="pb-2 text-right font-medium">Price</th>
                  </tr>
                </thead>
                <tbody>
                  {moversLoading ? (
                    <tr>
                      <td colSpan={4} className="py-5 text-center">
                        <div className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-edge border-t-brand" />
                      </td>
                    </tr>
                  ) : !movers || movers.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-5 text-center text-xs text-faint">
                        No data available
                      </td>
                    </tr>
                  ) : (
                    movers.map((mover, i) => {
                      const isPositive = mover.change_pct >= 0
                      return (
                        <tr
                          key={`${mover.exchange_code}-${mover.ticker}`}
                          className="border-b border-edge/20 last:border-0 hover:bg-raised/30 transition-colors"
                        >
                          <td className="py-2.5 pr-4 text-[11px] text-faint tabular-nums hidden sm:table-cell">
                            {i + 1}
                          </td>
                          <td className="py-2.5 pr-4">
                            <Link
                              to={`/market/${mover.exchange_code}/${mover.ticker}`}
                              className="font-mono text-sm font-semibold text-bright hover:text-brand transition-colors"
                            >
                              {mover.ticker}
                            </Link>
                          </td>
                          <td className="py-2.5 pr-4 text-xs text-dim truncate max-w-[140px]">
                            {mover.name}
                          </td>
                          <td className="py-2 text-right text-xs tabular-nums font-medium text-bright whitespace-nowrap">
                            {formatCurrency(Number(mover.current_price), mover.currency_code)}
                            <span className={`ml-1.5 text-[11px] font-semibold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                              {isPositive ? '+' : ''}{mover.change_pct.toFixed(2)}%
                            </span>
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </section>

            {/* Watchlist */}
            <section className="md:w-56 shrink-0 rounded-md border border-edge/30 px-4 py-3">
              <span className="text-sm font-semibold text-bright block mb-3">Watchlist</span>
              {!isAuthenticated ? (
                <p className="text-xs text-faint">
                  <Link to="/login" className="text-brand hover:underline">Sign in</Link>{' '}
                  to view your watchlist.
                </p>
              ) : (
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-edge/30 text-[11px] uppercase tracking-wider text-faint">
                      <th className="pb-2 pr-4 text-left font-medium w-20">Ticker</th>
                      <th className="pb-2 pr-4 text-left font-medium">Name</th>
                      <th className="pb-2 text-right font-medium">Price</th>
                    </tr>
                  </thead>
                  <tbody>
                    {watchlist.length === 0 ? (
                      <tr>
                        <td colSpan={3} className="pt-4 text-xs text-faint">
                          No assets in your watchlist.
                        </td>
                      </tr>
                    ) : (
                      watchlist.map(item => {
                        const isPositive = item.change_pct != null && item.change_pct >= 0
                        return (
                          <tr
                            key={`${item.exchange_code}-${item.ticker}`}
                            className="border-b border-edge/20 last:border-0 hover:bg-raised/30 transition-colors"
                          >
                            <td className="py-2.5 pr-4">
                              <Link
                                to={`/market/${item.exchange_code}/${item.ticker}`}
                                className="font-mono text-sm font-semibold text-bright hover:text-brand transition-colors"
                              >
                                {item.ticker}
                              </Link>
                            </td>
                            <td className="py-2.5 pr-4 text-xs text-dim truncate max-w-[100px]">
                              {item.name}
                            </td>
                            <td className="py-2 text-right text-xs tabular-nums font-medium text-bright whitespace-nowrap">
                              {item.current_price
                                ? formatCurrency(Number(item.current_price), item.currency_code)
                                : <span className="text-faint">—</span>}
                              {item.change_pct != null && (
                                <span className={`ml-1.5 text-[11px] font-semibold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                                  {isPositive ? '+' : ''}{item.change_pct.toFixed(2)}%
                                </span>
                              )}
                            </td>
                          </tr>
                        )
                      })
                    )}
                  </tbody>
                </table>
              )}
            </section>

          </div>

          {/* ── 4. Exchanges ────────────────────────────────────────── */}
          <section>
            <span className="text-[11px] uppercase tracking-wider text-faint block mb-3">
              Browse Exchanges
            </span>
            <div className="divide-y divide-edge/20">
              {(exchanges ?? []).map(exchange => (
                <Link
                  key={exchange.code}
                  to={`/market/${exchange.code}`}
                  className="group flex items-center gap-4 py-3 hover:bg-raised/30 transition-colors -mx-1 px-1 rounded"
                >
                  <span className="w-14 shrink-0 font-mono text-sm font-semibold text-bright group-hover:text-brand transition-colors">
                    {exchange.code}
                  </span>
                  <span className="flex-1 text-xs text-dim truncate min-w-0">
                    {exchange.name}
                  </span>
                  <StatusBadge value={exchange.is_open ? 'OPEN' : 'CLOSED'} />
                  <span className="hidden sm:block text-xs text-faint w-28 shrink-0 text-right">
                    {exchange.is_open
                      ? `${exchange.open_time}–${exchange.close_time}`
                      : exchange.hours_until_open != null
                        ? `Opens in ${exchange.hours_until_open}h`
                        : 'Closed'}
                  </span>
                  <span className="hidden md:block text-xs text-faint w-16 text-right shrink-0">
                    {exchange.asset_count} asset{exchange.asset_count !== 1 ? 's' : ''}
                  </span>
                  <ChevronRight className="size-3.5 text-faint/40 group-hover:text-faint transition-colors shrink-0" />
                </Link>
              ))}
            </div>
          </section>

        </div>
      )}

    </PageWrapper>
  )
}
