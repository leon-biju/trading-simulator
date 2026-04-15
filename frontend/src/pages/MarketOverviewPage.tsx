import { useState, useMemo, useRef, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search, X, Clock, Star, TrendingUp, TrendingDown } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import PageWrapper from '@/components/layout/PageWrapper'
import StatusBadge from '@/components/common/StatusBadge'
import EmptyState from '@/components/common/EmptyState'
import { getExchanges } from '@/api/market'
import { formatCurrency } from '@/lib/utils'
import { useAuth } from '@/auth/AuthContext'
import { useRecentlyViewed } from '@/hooks/useRecentlyViewed'

const CATEGORY_LABELS: Record<string, string> = {
  STOCK: 'Stocks',
  ETF: 'ETFs',
  CRYPTO: 'Crypto',
}

// ─── Local sub-components ────────────────────────────────────────────────────

interface SectionCardProps {
  title: string
  icon: LucideIcon
  accentClass?: string
  children: React.ReactNode
}

function SectionCard({ title, icon: Icon, accentClass = 'text-faint', children }: SectionCardProps) {
  return (
    <div className="rounded-lg border border-edge bg-panel overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-edge">
        <Icon className={`size-3.5 ${accentClass}`} strokeWidth={2} />
        <span className="text-[11px] uppercase tracking-wider text-faint font-medium">{title}</span>
      </div>
      {children}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function MarketOverviewPage() {
  const [search, setSearch] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [dropdownIndex, setDropdownIndex] = useState(-1)
  const [activeCategory, setActiveCategory] = useState<string | null>(null)

  const searchRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const { recent } = useRecentlyViewed()

  const { data: exchanges, isLoading } = useQuery({
    queryKey: ['exchanges'],
    queryFn: getExchanges,
    staleTime: 5 * 60_000,
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

  const assetTypes = useMemo(() => {
    const types = new Set(allAssets.map(a => a.asset_type))
    return Array.from(types).sort()
  }, [allAssets])

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

  const filteredAssets = useMemo(() => {
    if (!activeCategory) return []
    return allAssets.filter(a => a.asset_type === activeCategory)
  }, [activeCategory, allAssets])

  const filteredExchanges = useMemo(() => {
    if (!exchanges) return []
    if (!activeCategory) return exchanges
    return exchanges
      .map(e => ({ ...e, assets: e.assets.filter(a => a.asset_type === activeCategory) }))
      .filter(e => e.assets.length > 0)
  }, [exchanges, activeCategory])

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

  return (
    <PageWrapper>
      {/* ── Search ─────────────────────────────────────────────────────── */}
      <div className="mb-5">
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
                    <div className="border-t border-edge px-4 py-2 text-center text-[11px] text-faint">
                      Showing 8 of {typeaheadTotal} results
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Category shortcuts ──────────────────────────────────────────── */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-0.5">
        <button
          onClick={() => setActiveCategory(null)}
          className={`shrink-0 rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors ${
            activeCategory === null
              ? 'border-brand bg-brand/10 text-brand'
              : 'border-edge text-faint hover:text-dim hover:border-edge/80'
          }`}
        >
          All
        </button>
        {assetTypes.map(type => (
          <button
            key={type}
            onClick={() => setActiveCategory(type === activeCategory ? null : type)}
            className={`shrink-0 rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors ${
              activeCategory === type
                ? 'border-brand bg-brand/10 text-brand'
                : 'border-edge text-faint hover:text-dim hover:border-edge/80'
            }`}
          >
            {CATEGORY_LABELS[type] ?? type}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex h-40 items-center justify-center">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-edge border-t-brand" />
        </div>
      ) : (
        <>
          {/* ── Recently Viewed + Watchlist ─────────────────────────────── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <SectionCard title="Recently Viewed" icon={Clock}>
              {recent.length === 0 ? (
                <EmptyState
                  icon={Clock}
                  title="No recent assets"
                  description="Assets you visit will appear here"
                />
              ) : (
                <div className="divide-y divide-edge/40">
                  {recent.slice(0, 5).map(item => (
                    <Link
                      key={`${item.exchangeCode}-${item.ticker}`}
                      to={`/market/${item.exchangeCode}/${item.ticker}`}
                      className="flex items-center gap-3 px-4 py-2.5 hover:bg-raised/50 transition-colors"
                    >
                      <span className="w-16 shrink-0 font-mono text-sm font-semibold text-bright">
                        {item.ticker}
                      </span>
                      <span className="flex-1 text-xs text-dim truncate">{item.name}</span>
                      <span className="text-xs tabular-nums font-medium text-bright">
                        {item.price ? formatCurrency(item.price, item.currency) : '—'}
                      </span>
                    </Link>
                  ))}
                </div>
              )}
            </SectionCard>

            <SectionCard title="Watchlist" icon={Star}>
              {!isAuthenticated ? (
                <div className="flex flex-col items-center justify-center gap-2 py-6 text-center">
                  <Star className="size-8 text-faint opacity-60" strokeWidth={1.5} />
                  <p className="text-sm text-dim">Sign in to see your watchlist</p>
                  <Link to="/login" className="text-xs text-brand hover:underline">
                    Sign in
                  </Link>
                </div>
              ) : (
                <EmptyState
                  icon={Star}
                  title="Watchlist coming soon"
                  description="Save assets for quick access"
                />
              )}
            </SectionCard>
          </div>

          {/* ── Top Gainers + Top Losers ────────────────────────────────── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <SectionCard title="Top Gainers" icon={TrendingUp} accentClass="text-buy">
              <EmptyState
                icon={TrendingUp}
                title="Coming soon"
                description="Top performers, refreshed every 30s"
              />
            </SectionCard>
            <SectionCard title="Top Losers" icon={TrendingDown} accentClass="text-sell">
              <EmptyState
                icon={TrendingDown}
                title="Coming soon"
                description="Biggest decliners, refreshed every 30s"
              />
            </SectionCard>
          </div>

          {/* ── Browse ─────────────────────────────────────────────────── */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] uppercase tracking-wider text-faint font-medium">
                {activeCategory
                  ? `${CATEGORY_LABELS[activeCategory] ?? activeCategory} — all exchanges`
                  : 'Browse by Exchange'}
              </span>
              {activeCategory && (
                <span className="text-[11px] text-faint">
                  {filteredAssets.length} asset{filteredAssets.length !== 1 ? 's' : ''}
                </span>
              )}
            </div>

            {activeCategory ? (
              <div className="rounded-lg border border-edge bg-panel overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-edge text-[11px] uppercase tracking-wider text-faint">
                      <th className="px-4 py-3 text-left font-medium">Ticker</th>
                      <th className="px-4 py-3 text-left font-medium">Name</th>
                      <th className="px-4 py-3 text-left font-medium hidden sm:table-cell">
                        Exchange
                      </th>
                      <th className="px-4 py-3 text-right font-medium">Price</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredAssets.map(asset => (
                      <tr
                        key={`${asset.exchangeCode}-${asset.ticker}`}
                        className="border-b border-edge/40 last:border-0 hover:bg-raised/50 transition-colors cursor-pointer"
                        onClick={() => navigate(`/market/${asset.exchangeCode}/${asset.ticker}`)}
                      >
                        <td className="px-4 py-2.5">
                          <span className="text-sm font-semibold text-bright font-mono">
                            {asset.ticker}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 text-xs text-dim">{asset.name}</td>
                        <td className="px-4 py-2.5 hidden sm:table-cell">
                          <Link
                            to={`/market/${asset.exchangeCode}`}
                            onClick={e => e.stopPropagation()}
                            className="inline-flex items-center rounded border border-edge/60 bg-raised px-2 py-0.5 text-[11px] text-faint font-mono hover:text-dim hover:border-edge transition-colors"
                          >
                            {asset.exchangeCode}
                          </Link>
                        </td>
                        <td className="px-4 py-2.5 text-right tabular-nums text-xs font-medium text-bright">
                          {asset.current_price
                            ? formatCurrency(asset.current_price, asset.currency_code)
                            : <span className="text-faint">—</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {filteredExchanges.map(exchange => (
                  <Link
                    key={exchange.code}
                    to={`/market/${exchange.code}`}
                    className="group rounded-lg border border-edge bg-panel hover:bg-raised hover:border-edge/80 transition-all p-4"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-bright group-hover:text-brand transition-colors truncate">
                          {exchange.name}
                        </p>
                        <span className="text-[11px] text-faint font-mono">{exchange.code}</span>
                      </div>
                      <StatusBadge value={exchange.is_open ? 'OPEN' : 'CLOSED'} />
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] text-faint">
                        {exchange.is_open
                          ? `${exchange.open_time}–${exchange.close_time}`
                          : exchange.hours_until_open != null
                            ? `Opens in ${exchange.hours_until_open}h`
                            : 'Closed'}
                      </span>
                      <span className="text-[11px] text-faint">
                        {exchange.asset_count} asset{exchange.asset_count !== 1 ? 's' : ''}
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </PageWrapper>
  )
}
