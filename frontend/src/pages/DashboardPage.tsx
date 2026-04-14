import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Wallet, ClipboardList, TrendingUp, BarChart3, ArrowUpRight, ArrowDownRight } from 'lucide-react'
import PageWrapper from '@/components/layout/PageWrapper'
import PortfolioChart from '@/components/charts/PortfolioChart'
import PnlBadge from '@/components/common/PnlBadge'
import StatusBadge from '@/components/common/StatusBadge'
import EmptyState from '@/components/common/EmptyState'
import { useAuth } from '@/auth/AuthContext'
import { getPortfolio, cancelOrder, getTrades, getOrders } from '@/api/trading'
import { getWallets } from '@/api/wallets'
import { formatCurrency, formatDateShort } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

export default function DashboardPage() {
  const { user } = useAuth()
  const qc = useQueryClient()

  const { data: portfolio, isLoading: portfolioLoading } = useQuery({
    queryKey: ['portfolio'],
    queryFn: getPortfolio,
    staleTime: 30_000,
  })
  const { data: wallets, isLoading: walletsLoading } = useQuery({
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

  const homeCurrency  = user?.home_currency ?? 'GBP'
  const pendingOrders = orders?.results.filter((o) => o.status === 'PENDING') ?? []
  const recentTrades  = trades?.results.slice(0, 6) ?? []
  const totalAssets   =
    portfolio && user?.total_cash
      ? (parseFloat(portfolio.total_value) + parseFloat(user.total_cash)).toFixed(2)
      : null

  const displayName   = user?.display_name || user?.username || ''
  const hour          = new Date().getHours()
  const greeting      =
    hour >= 5 && hour < 12 ? 'Good morning' :
    hour >= 12 && hour < 18 ? 'Good afternoon' :
    'Good evening';
  const pnlValue      = portfolio?.total_pnl != null ? parseFloat(portfolio.total_pnl) : null
  const pnlPositive   = pnlValue != null && pnlValue > 0
  const pnlNegative   = pnlValue != null && pnlValue < 0

  return (
    <PageWrapper>

      {/* ── Welcome + metrics ────────────────────────────────── */}
      <div className="mb-6">
        {/* Welcome line */}
        {displayName && (
          <p className="text-2xl font-semibold text-bright mb-3">
            {greeting}, {displayName}
          </p>
        )}

        {/* Total assets row */}
        {portfolioLoading ? (
          <div className="space-y-2">
            <div className="flex items-baseline gap-4">
              <Skeleton className="h-9 w-40" />
              <Skeleton className="h-5 w-28" />
            </div>
            <Skeleton className="h-3 w-52" />
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span className="text-4xl font-semibold tabular-nums text-bright leading-none">
                {formatCurrency(totalAssets, homeCurrency)}
              </span>
              {pnlValue !== null && (
                <span className={`flex items-center gap-0.5 text-sm font-medium tabular-nums ${pnlPositive ? 'text-buy' : pnlNegative ? 'text-sell' : 'text-faint'}`}>
                  {pnlPositive ? (
                    <ArrowUpRight className="size-3.5" />
                  ) : pnlNegative ? (
                    <ArrowDownRight className="size-3.5" />
                  ) : null}
                  {pnlPositive ? '+' : ''}{formatCurrency(portfolio?.total_pnl, homeCurrency)}
                  {portfolio?.pnl_percent != null && (
                    <span className="ml-0.5">
                      ({pnlPositive ? '+' : ''}{portfolio.pnl_percent.toFixed(2)}%)
                    </span>
                  )}
                </span>
              )}
            </div>
            <p className="text-xs text-faint mt-1.5">
              <span className="tabular-nums">{formatCurrency(portfolio?.total_value, homeCurrency)}</span>
              {' invested · '}
              <span className="tabular-nums">{formatCurrency(user?.total_cash, homeCurrency)}</span>
              {' cash'}
            </p>
          </>
        )}
      </div>

      {/* ── Main layout: left (chart + holdings) | right (activity) */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_minmax(0,320px)]">

        {/* Left: chart flowing into holdings */}
        <div className="flex flex-col gap-6">
          <div className="h-[380px]">
            <PortfolioChart />
          </div>

          {(portfolio?.positions.length ?? 0) > 0 && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <TrendingUp className="size-3.5 text-faint" />
                  <span className="text-[11px] uppercase tracking-wider text-faint font-medium">Holdings</span>
                </div>
                <Button variant="link" size="sm" className="h-auto p-0 text-[11px] text-brand" asChild>
                  <Link to="/portfolio">Full portfolio →</Link>
                </Button>
              </div>
              <Table>
                <TableHeader>
                  <TableRow className="border-b border-edge hover:bg-transparent">
                    <TableHead className="px-3 py-2.5 text-[11px] uppercase tracking-wider text-faint font-medium">Asset</TableHead>
                    <TableHead className="px-3 py-2.5 text-right text-[11px] uppercase tracking-wider text-faint font-medium">Qty</TableHead>
                    <TableHead className="px-3 py-2.5 text-right text-[11px] uppercase tracking-wider text-faint font-medium">Avg cost</TableHead>
                    <TableHead className="px-3 py-2.5 text-right text-[11px] uppercase tracking-wider text-faint font-medium">Price</TableHead>
                    <TableHead className="px-3 py-2.5 text-right text-[11px] uppercase tracking-wider text-faint font-medium">P&amp;L</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {portfolio?.positions.map((p) => (
                    <TableRow key={p.id} className="border-b border-edge/40 last:border-0 hover:bg-raised/40 transition-colors">
                      <TableCell className="px-3 py-2.5">
                        <Link to={`/market/${p.exchange_code}/${p.asset_ticker}`} className="font-medium text-bright hover:text-brand transition-colors">
                          {p.asset_ticker}
                        </Link>
                        <span className="ml-1.5 text-[11px] text-faint">{p.exchange_code}</span>
                      </TableCell>
                      <TableCell className="px-3 py-2.5 text-right tabular-nums text-dim text-xs">{p.quantity}</TableCell>
                      <TableCell className="px-3 py-2.5 text-right tabular-nums text-dim text-xs">{formatCurrency(p.avg_cost_home, homeCurrency)}</TableCell>
                      <TableCell className="px-3 py-2.5 text-right tabular-nums text-dim text-xs">{formatCurrency(p.current_price_home, homeCurrency)}</TableCell>
                      <TableCell className="px-3 py-2.5 text-right">
                        <PnlBadge value={p.unrealized_pnl_home} currency={homeCurrency} percent={p.pnl_percent} size="sm" />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>

        {/* Right: pending orders, recent trades, wallets — stacked cards */}
        <div className="flex flex-col gap-4">

          {/* Pending orders card */}
          <Card className="bg-panel border-edge">
            <CardHeader className="pb-2 px-4 pt-4 flex-row items-center justify-between space-y-0">
              <CardTitle className="text-[11px] uppercase tracking-wider text-faint font-medium">
                Pending orders
              </CardTitle>
              <Button variant="link" size="sm" className="h-auto p-0 text-[11px] text-brand" asChild>
                <Link to="/portfolio?tab=orders">View all</Link>
              </Button>
            </CardHeader>
            <CardContent className="px-2 pb-3">
              {pendingOrders.length === 0 ? (
                <EmptyState icon={ClipboardList} title="No pending orders" />
              ) : (
                <div className="space-y-1">
                  {pendingOrders.slice(0, 4).map((o) => (
                    <div key={o.id} className="flex items-center justify-between rounded-md bg-raised/50 px-2 py-2">
                      <div>
                        <p className="text-xs font-medium text-bright">
                          {o.asset_ticker}
                          <span className="ml-1.5 text-[11px] text-faint">{o.exchange_code}</span>
                        </p>
                        <div className="mt-0.5 flex items-center gap-1.5">
                          <StatusBadge value={o.side} />
                          <span className="text-[11px] text-dim">{o.quantity}{o.limit_price && ` @ ${o.limit_price}`}</span>
                        </div>
                      </div>
                      <Button variant="ghost" size="sm" className="h-7 px-2 text-[11px] text-sell hover:text-sell hover:bg-sell/10" onClick={() => cancelMutation.mutate(o.id)} disabled={cancelMutation.isPending}>
                        Cancel
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recent trades card */}
          <Card className="bg-panel border-edge">
            <CardHeader className="pb-2 px-4 pt-4 flex-row items-center justify-between space-y-0">
              <CardTitle className="text-[11px] uppercase tracking-wider text-faint font-medium">
                Recent trades
              </CardTitle>
              <Button variant="link" size="sm" className="h-auto p-0 text-[11px] text-brand" asChild>
                <Link to="/portfolio?tab=trades">View all →</Link>
              </Button>
            </CardHeader>
            <CardContent className="px-2 pb-3">
              {recentTrades.length === 0 ? (
                <EmptyState icon={BarChart3} title="No recent trades" />
              ) : (
                <div className="space-y-0.5">
                  {recentTrades.map((t) => (
                    <div key={t.id} className="flex items-center gap-2 rounded-md px-2 py-2 hover:bg-raised/30 transition-colors">
                      <span className="w-20 shrink-0 text-[11px] text-faint tabular-nums">{formatDateShort(t.executed_at)}</span>
                      <div className="flex-1 min-w-0">
                        <span className="text-xs font-medium text-bright">{t.asset_ticker}</span>
                        <span className="ml-1 text-[11px] text-faint">{t.exchange_code}</span>
                      </div>
                      <StatusBadge value={t.side} />
                      <span className="text-xs tabular-nums text-bright shrink-0">
                        {t.total_value_home
                          ? formatCurrency(t.total_value_home, homeCurrency)
                          : formatCurrency(t.total_value, t.asset_currency_code)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Cash wallets card */}
          <Card className="bg-panel border-edge">
            <CardHeader className="pb-2 px-4 pt-4 flex-row items-center justify-between space-y-0">
              <CardTitle className="text-[11px] uppercase tracking-wider text-faint font-medium">
                Cash wallets
              </CardTitle>
            </CardHeader>
            <CardContent className="px-2 pb-3">
              {walletsLoading ? (
                <div className="space-y-2 px-2">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="flex justify-between">
                      <Skeleton className="h-4 w-10" />
                      <Skeleton className="h-4 w-24" />
                    </div>
                  ))}
                </div>
              ) : wallets?.length ? (
                wallets.map((w) => (
                  <Link
                    key={w.currency_code}
                    to={`/wallets/${w.currency_code}`}
                    className="flex items-center justify-between rounded-md px-2 py-2 transition hover:bg-raised"
                  >
                    <span className="text-xs font-semibold text-dim font-mono">{w.currency_code}</span>
                    <div className="text-right">
                      <p className="text-xs tabular-nums text-bright">{formatCurrency(w.available_balance, w.currency_code)}</p>
                      {parseFloat(w.pending_balance) > 0 && (
                        <p className="text-[11px] text-faint">{formatCurrency(w.pending_balance, w.currency_code)} reserved</p>
                      )}
                    </div>
                  </Link>
                ))
              ) : (
                <EmptyState icon={Wallet} title="No wallets" />
              )}
            </CardContent>
          </Card>

        </div>
      </div>
    </PageWrapper>
  )
}
