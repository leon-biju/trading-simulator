import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import PageWrapper from '@/components/layout/PageWrapper'
import PortfolioChart from '@/components/charts/PortfolioChart'
import PnlBadge from '@/components/common/PnlBadge'
import StatusBadge from '@/components/common/StatusBadge'
import { useAuth } from '@/auth/AuthContext'
import { getPortfolio, getOrders, getTrades, cancelOrder } from '@/api/trading'
import { formatCurrency, formatDate } from '@/lib/utils'

type Tab = 'holdings' | 'orders' | 'trades'

function Spinner() {
  return (
    <div className="flex h-40 items-center justify-center">
      <div className="h-4 w-4 animate-spin rounded-full border-2 border-edge border-t-accent" />
    </div>
  )
}

/* ── Pagination helper ───────────────────────────────────────── */
function Pagination({
  count, page, hasNext, hasPrev, onPage,
}: {
  count: number; page: number; hasNext: boolean; hasPrev: boolean; onPage: (n: number) => void
}) {
  if (count <= 25) return null
  return (
    <div className="flex items-center justify-between border-t border-edge px-4 py-3">
      <span className="text-[11px] text-faint">{count} total</span>
      <div className="flex gap-2">
        <button
          onClick={() => onPage(page - 1)} disabled={!hasPrev}
          className="rounded px-3 py-1 text-xs text-dim disabled:opacity-30 hover:text-bright transition-colors"
        >← Prev</button>
        <button
          onClick={() => onPage(page + 1)} disabled={!hasNext}
          className="rounded px-3 py-1 text-xs text-dim disabled:opacity-30 hover:text-bright transition-colors"
        >Next →</button>
      </div>
    </div>
  )
}

/* ── Holdings tab ─────────────────────────────────────────────── */
function HoldingsTab({ homeCurrency }: { homeCurrency: string }) {
  const { data: portfolio, isLoading } = useQuery({
    queryKey: ['portfolio'],
    queryFn: getPortfolio,
    staleTime: 30_000,
  })

  if (isLoading) return <Spinner />

  if ((portfolio?.positions.length ?? 0) === 0) {
    return (
      <div className="py-16 text-center">
        <p className="text-sm text-dim">No open positions.</p>
        <Link to="/market" className="mt-2 block text-xs text-accent hover:text-accent/80">Browse markets →</Link>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-edge text-[11px] uppercase tracking-wider text-faint">
            <th className="px-4 py-3 text-left font-medium">Asset</th>
            <th className="px-4 py-3 text-right font-medium">Qty</th>
            <th className="px-4 py-3 text-right font-medium">Avg cost</th>
            <th className="px-4 py-3 text-right font-medium">Price</th>
            <th className="px-4 py-3 text-right font-medium">Value</th>
            <th className="px-4 py-3 text-right font-medium">Unrealised P&L</th>
            <th className="px-4 py-3 text-right font-medium hidden lg:table-cell">Realised P&L</th>
          </tr>
        </thead>
        <tbody>
          {portfolio?.positions.map((p) => (
            <tr key={p.id} className="border-b border-edge/50 last:border-0 hover:bg-raised/40 transition-colors">
              <td className="px-4 py-2.5">
                <Link to={`/market/${p.exchange_code}/${p.asset_ticker}`}
                  className="font-semibold text-bright hover:text-accent transition-colors text-sm">
                  {p.asset_ticker}
                </Link>
                <span className="ml-1.5 text-[11px] text-faint">{p.exchange_code}</span>
                <p className="text-[11px] text-faint">{p.asset_name}</p>
              </td>
              <td className="px-4 py-2.5 text-right tabular-nums text-xs text-dim">{p.quantity}</td>
              <td className="px-4 py-2.5 text-right tabular-nums text-xs text-dim">
                {formatCurrency(p.avg_cost_home, homeCurrency)}
              </td>
              <td className="px-4 py-2.5 text-right tabular-nums text-xs text-dim">
                {formatCurrency(p.current_price_home, homeCurrency)}
              </td>
              <td className="px-4 py-2.5 text-right tabular-nums text-xs text-bright">
                {formatCurrency(p.current_value_home, homeCurrency)}
              </td>
              <td className="px-4 py-2.5 text-right">
                <PnlBadge value={p.unrealized_pnl_home} currency={homeCurrency} percent={p.pnl_percent} size="sm" />
              </td>
              <td className="px-4 py-2.5 text-right hidden lg:table-cell">
                <PnlBadge value={p.realized_pnl_home} currency={homeCurrency} size="sm" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ── Orders tab ───────────────────────────────────────────────── */
function OrdersTab() {
  const [page, setPage] = useState(1)
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['orders', page],
    queryFn: () => getOrders(page),
    staleTime: 5_000,
  })

  const cancelMutation = useMutation({
    mutationFn: cancelOrder,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['orders'] }),
  })

  if (isLoading) return <Spinner />

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-edge text-[11px] uppercase tracking-wider text-faint">
              <th className="px-4 py-3 text-left font-medium">Date</th>
              <th className="px-4 py-3 text-left font-medium">Asset</th>
              <th className="px-4 py-3 text-left font-medium">Side</th>
              <th className="px-4 py-3 text-left font-medium">Type</th>
              <th className="px-4 py-3 text-right font-medium">Qty</th>
              <th className="px-4 py-3 text-right font-medium">Limit</th>
              <th className="px-4 py-3 text-left font-medium">Status</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {(data?.results ?? []).map((o) => (
              <tr key={o.id} className="border-b border-edge/40 last:border-0 hover:bg-raised/40 transition-colors">
                <td className="px-4 py-2.5 text-[11px] text-faint">{formatDate(o.created_at)}</td>
                <td className="px-4 py-2.5">
                  <span className="text-sm font-semibold text-bright">{o.asset_ticker}</span>
                  <span className="ml-1.5 text-[11px] text-faint">{o.exchange_code}</span>
                </td>
                <td className="px-4 py-2.5"><StatusBadge value={o.side} /></td>
                <td className="px-4 py-2.5 text-xs text-faint">{o.order_type}</td>
                <td className="px-4 py-2.5 text-right tabular-nums text-xs text-dim">{o.quantity}</td>
                <td className="px-4 py-2.5 text-right tabular-nums text-xs text-faint">
                  {o.limit_price ?? '—'}
                </td>
                <td className="px-4 py-2.5"><StatusBadge value={o.status} /></td>
                <td className="px-4 py-2.5 text-right">
                  {o.status === 'PENDING' && (
                    <button
                      onClick={() => cancelMutation.mutate(o.id)}
                      disabled={cancelMutation.isPending}
                      className="text-[11px] text-sell hover:text-sell/80 disabled:opacity-40"
                    >Cancel</button>
                  )}
                </td>
              </tr>
            ))}
            {!data?.results.length && (
              <tr><td colSpan={8} className="px-4 py-12 text-center text-sm text-faint">No orders yet</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {data && <Pagination count={data.count} page={page} hasNext={!!data.next} hasPrev={!!data.previous} onPage={setPage} />}
    </>
  )
}

/* ── Trades tab ───────────────────────────────────────────────── */
function TradesTab({ homeCurrency }: { homeCurrency: string }) {
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['trades', page],
    queryFn: () => getTrades(page),
    staleTime: 5_000,
  })

  if (isLoading) return <Spinner />

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-edge text-[11px] uppercase tracking-wider text-faint">
              <th className="px-4 py-3 text-left font-medium">Executed</th>
              <th className="px-4 py-3 text-left font-medium">Asset</th>
              <th className="px-4 py-3 text-left font-medium">Side</th>
              <th className="px-4 py-3 text-right font-medium">Qty</th>
              <th className="px-4 py-3 text-right font-medium">Price</th>
              <th className="px-4 py-3 text-right font-medium">Total</th>
              <th className="px-4 py-3 text-right font-medium hidden lg:table-cell">Fee</th>
              <th className="px-4 py-3 text-right font-medium hidden lg:table-cell">Net</th>
            </tr>
          </thead>
          <tbody>
            {(data?.results ?? []).map((t) => (
              <tr key={t.id} className="border-b border-edge/40 last:border-0 hover:bg-raised/40 transition-colors">
                <td className="px-4 py-2.5 text-[11px] text-faint">{formatDate(t.executed_at)}</td>
                <td className="px-4 py-2.5">
                  <span className="text-sm font-semibold text-bright">{t.asset_ticker}</span>
                  <span className="ml-1.5 text-[11px] text-faint">{t.exchange_code}</span>
                </td>
                <td className="px-4 py-2.5"><StatusBadge value={t.side} /></td>
                <td className="px-4 py-2.5 text-right tabular-nums text-xs text-dim">{t.quantity}</td>
                <td className="px-4 py-2.5 text-right tabular-nums text-xs text-dim">
                  {t.price_home ? formatCurrency(t.price_home, homeCurrency) : formatCurrency(t.price, t.asset_currency_code)}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums text-xs text-bright">
                  {t.total_value_home ? formatCurrency(t.total_value_home, homeCurrency) : formatCurrency(t.total_value, t.asset_currency_code)}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums text-xs text-faint hidden lg:table-cell">
                  {t.fee_home ? formatCurrency(t.fee_home, homeCurrency) : formatCurrency(t.fee, t.fee_currency_code)}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums text-xs text-dim hidden lg:table-cell">
                  {t.net_amount_home ? formatCurrency(t.net_amount_home, homeCurrency) : formatCurrency(t.net_amount, t.asset_currency_code)}
                </td>
              </tr>
            ))}
            {!data?.results.length && (
              <tr><td colSpan={8} className="px-4 py-12 text-center text-sm text-faint">No trades yet</td></tr>
            )}
          </tbody>
        </table>
      </div>
      {data && <Pagination count={data.count} page={page} hasNext={!!data.next} hasPrev={!!data.previous} onPage={setPage} />}
    </>
  )
}

/* ── Page ─────────────────────────────────────────────────────── */
export default function PortfolioPage() {
  const { user } = useAuth()
  const homeCurrency = user?.home_currency ?? 'GBP'
  const [searchParams, setSearchParams] = useSearchParams()
  const activeTab = (searchParams.get('tab') as Tab) ?? 'holdings'

  const { data: portfolio } = useQuery({
    queryKey: ['portfolio'],
    queryFn: getPortfolio,
    staleTime: 30_000,
  })

  const tabs: { id: Tab; label: string }[] = [
    { id: 'holdings', label: 'Holdings' },
    { id: 'orders',   label: 'Orders' },
    { id: 'trades',   label: 'Trades' },
  ]

  const tabCls = (id: Tab) =>
    `px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
      activeTab === id
        ? 'border-accent text-accent'
        : 'border-transparent text-faint hover:text-dim'
    }`

  return (
    <PageWrapper>
      {/* ── Summary cards ───────────────────────────────────── */}
      <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {[
          { label: 'Market value',   value: formatCurrency(portfolio?.total_value, homeCurrency) },
          { label: 'Cost basis',     value: formatCurrency(portfolio?.total_cost, homeCurrency) },
          { label: 'Unrealised P&L', value: <PnlBadge value={portfolio?.total_pnl} currency={homeCurrency} percent={portfolio?.pnl_percent} /> },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-lg border border-edge bg-panel px-4 py-3">
            <p className="mb-1 text-[11px] uppercase tracking-wider text-faint">{label}</p>
            <div className="text-base font-semibold text-bright">{value}</div>
          </div>
        ))}
      </div>

      {/* ── Chart (holdings view only) ──────────────────────── */}
      {activeTab === 'holdings' && (
        <div className="mb-5 rounded-lg border border-edge bg-panel p-4" style={{ height: 260 }}>
          <PortfolioChart />
        </div>
      )}

      {/* ── Tabs + table ────────────────────────────────────── */}
      <div className="rounded-lg border border-edge bg-panel">
        <div className="flex border-b border-edge">
          {tabs.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setSearchParams({ tab: id })}
              className={tabCls(id)}
            >
              {label}
            </button>
          ))}
        </div>

        {activeTab === 'holdings' && <HoldingsTab homeCurrency={homeCurrency} />}
        {activeTab === 'orders'   && <OrdersTab />}
        {activeTab === 'trades'   && <TradesTab homeCurrency={homeCurrency} />}
      </div>
    </PageWrapper>
  )
}
