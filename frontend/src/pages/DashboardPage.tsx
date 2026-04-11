import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Wallet, ClipboardList, TrendingUp, BarChart3 } from 'lucide-react'
import PageWrapper from '@/components/layout/PageWrapper'
import PortfolioChart from '@/components/charts/PortfolioChart'
import PnlBadge from '@/components/common/PnlBadge'
import StatusBadge from '@/components/common/StatusBadge'
import StatCard from '@/components/common/StatCard'
import EmptyState from '@/components/common/EmptyState'
import { useAuth } from '@/auth/AuthContext'
import { getPortfolio, cancelOrder, getTrades, getOrders } from '@/api/trading'
import { getWallets } from '@/api/wallets'
import { formatCurrency, formatDateShort } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
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

  const pnlValue = portfolio?.total_pnl != null ? parseFloat(portfolio.total_pnl) : null
  const pnlTrend = pnlValue != null ? {
    direction: (pnlValue > 0 ? 'up' : pnlValue < 0 ? 'down' : 'neutral') as 'up' | 'down' | 'neutral',
    label: portfolio?.pnl_percent != null
      ? `${pnlValue >= 0 ? '+' : ''}${portfolio.pnl_percent.toFixed(2)}%`
      : '',
  } : undefined

  return (
    <PageWrapper>
      {/* ── KPI row ──────────────────────────────────────────── */}
      <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {portfolioLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="bg-panel border-edge">
              <CardContent className="px-4 py-3">
                <Skeleton className="mb-2 h-3 w-20" />
                <Skeleton className="h-6 w-28" />
              </CardContent>
            </Card>
          ))
        ) : (
          <>
            <StatCard
              label="Total assets"
              value={formatCurrency(totalAssets, homeCurrency)}
            />
            <StatCard
              label="Investments"
              value={formatCurrency(portfolio?.total_value, homeCurrency)}
            />
            <StatCard
              label="Cash"
              value={formatCurrency(user?.total_cash, homeCurrency)}
            />
            <StatCard
              label="Unrealised P&L"
              value={<PnlBadge value={portfolio?.total_pnl} currency={homeCurrency} percent={portfolio?.pnl_percent} />}
              trend={pnlTrend}
            />
          </>
        )}
      </div>

      {/* ── Chart + side panel ───────────────────────────────── */}
      <div className="mb-5 grid grid-cols-1 gap-4 lg:grid-cols-3" style={{ minHeight: 340 }}>
        {/* Portfolio chart */}
        <Card className="bg-panel border-edge lg:col-span-2 flex flex-col" style={{ minHeight: 300 }}>
          <CardContent className="flex-1 min-h-0 p-4">
            <PortfolioChart />
          </CardContent>
        </Card>

        {/* Right column */}
        <div className="flex flex-col gap-4">
          {/* Cash wallets */}
          <Card className="bg-panel border-edge flex-1">
            <CardHeader className="pb-2 px-4 pt-4">
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
                      <Skeleton className="h-4 w-20" />
                    </div>
                  ))}
                </div>
              ) : wallets?.length ? (
                <ScrollArea className="max-h-44">
                  {wallets.map((w) => (
                    <Link
                      key={w.currency_code}
                      to={`/wallets/${w.currency_code}`}
                      className="flex items-center justify-between rounded-md px-2 py-2 transition hover:bg-raised"
                    >
                      <span className="text-xs font-semibold text-dim font-mono">{w.currency_code}</span>
                      <div className="text-right">
                        <p className="text-xs tabular-nums text-bright">
                          {formatCurrency(w.available_balance, w.currency_code)}
                        </p>
                        {parseFloat(w.pending_balance) > 0 && (
                          <p className="text-[11px] text-faint">
                            {formatCurrency(w.pending_balance, w.currency_code)} reserved
                          </p>
                        )}
                      </div>
                    </Link>
                  ))}
                </ScrollArea>
              ) : (
                <EmptyState icon={Wallet} title="No wallets" />
              )}
            </CardContent>
          </Card>

          {/* Pending orders */}
          <Card className="bg-panel border-edge flex-1">
            <CardHeader className="pb-2 px-4 pt-4 flex-row items-center justify-between space-y-0">
              <CardTitle className="text-[11px] uppercase tracking-wider text-faint font-medium">
                Pending orders
              </CardTitle>
              <Button variant="link" size="sm" className="h-auto p-0 text-[11px] text-accent" asChild>
                <Link to="/portfolio?tab=orders">View all</Link>
              </Button>
            </CardHeader>
            <CardContent className="px-2 pb-3">
              {pendingOrders.length === 0 ? (
                <EmptyState icon={ClipboardList} title="No pending orders" />
              ) : (
                <div className="space-y-1">
                  {pendingOrders.slice(0, 4).map((o) => (
                    <div
                      key={o.id}
                      className="flex items-center justify-between rounded-md bg-raised/50 px-2 py-2"
                    >
                      <div>
                        <p className="text-xs font-medium text-bright">
                          {o.asset_ticker}
                          <span className="ml-1.5 text-[11px] text-faint">{o.exchange_code}</span>
                        </p>
                        <div className="mt-0.5 flex items-center gap-1.5">
                          <StatusBadge value={o.side} />
                          <span className="text-[11px] text-dim">
                            {o.quantity}{o.limit_price && ` @ ${o.limit_price}`}
                          </span>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2 text-[11px] text-sell hover:text-sell hover:bg-sell/10"
                        onClick={() => cancelMutation.mutate(o.id)}
                        disabled={cancelMutation.isPending}
                      >
                        Cancel
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* ── Holdings table ───────────────────────────────────── */}
      {(portfolio?.positions.length ?? 0) > 0 && (
        <Card className="mb-5 bg-panel border-edge">
          <CardHeader className="flex-row items-center justify-between space-y-0 px-4 py-3 border-b border-edge">
            <div className="flex items-center gap-2">
              <TrendingUp className="size-3.5 text-faint" />
              <CardTitle className="text-[11px] uppercase tracking-wider text-faint font-medium">
                Holdings
              </CardTitle>
            </div>
            <Button variant="link" size="sm" className="h-auto p-0 text-[11px] text-accent" asChild>
              <Link to="/portfolio">Full portfolio →</Link>
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="border-b border-edge hover:bg-transparent">
                  <TableHead className="px-4 py-2.5 text-[11px] uppercase tracking-wider text-faint font-medium">
                    Asset
                  </TableHead>
                  <TableHead className="px-4 py-2.5 text-right text-[11px] uppercase tracking-wider text-faint font-medium">
                    Qty
                  </TableHead>
                  <TableHead className="px-4 py-2.5 text-right text-[11px] uppercase tracking-wider text-faint font-medium">
                    Avg cost
                  </TableHead>
                  <TableHead className="px-4 py-2.5 text-right text-[11px] uppercase tracking-wider text-faint font-medium">
                    Price
                  </TableHead>
                  <TableHead className="px-4 py-2.5 text-right text-[11px] uppercase tracking-wider text-faint font-medium">
                    P&amp;L
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {portfolio?.positions.map((p) => (
                  <TableRow
                    key={p.id}
                    className="border-b border-edge/40 last:border-0 hover:bg-raised/40 transition-colors"
                  >
                    <TableCell className="px-4 py-2.5">
                      <Link
                        to={`/market/${p.exchange_code}/${p.asset_ticker}`}
                        className="font-medium text-bright hover:text-accent transition-colors"
                      >
                        {p.asset_ticker}
                      </Link>
                      <span className="ml-1.5 text-[11px] text-faint">{p.exchange_code}</span>
                    </TableCell>
                    <TableCell className="px-4 py-2.5 text-right tabular-nums text-dim text-xs">
                      {p.quantity}
                    </TableCell>
                    <TableCell className="px-4 py-2.5 text-right tabular-nums text-dim text-xs">
                      {formatCurrency(p.avg_cost_home, homeCurrency)}
                    </TableCell>
                    <TableCell className="px-4 py-2.5 text-right tabular-nums text-dim text-xs">
                      {formatCurrency(p.current_price_home, homeCurrency)}
                    </TableCell>
                    <TableCell className="px-4 py-2.5 text-right">
                      <PnlBadge
                        value={p.unrealized_pnl_home}
                        currency={homeCurrency}
                        percent={p.pnl_percent}
                        size="sm"
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* ── Recent trades ────────────────────────────────────── */}
      {recentTrades.length > 0 && (
        <Card className="bg-panel border-edge">
          <CardHeader className="flex-row items-center justify-between space-y-0 px-4 py-3 border-b border-edge">
            <div className="flex items-center gap-2">
              <BarChart3 className="size-3.5 text-faint" />
              <CardTitle className="text-[11px] uppercase tracking-wider text-faint font-medium">
                Recent trades
              </CardTitle>
            </div>
            <Button variant="link" size="sm" className="h-auto p-0 text-[11px] text-accent" asChild>
              <Link to="/portfolio?tab=trades">View all →</Link>
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableBody>
                {recentTrades.map((t) => (
                  <TableRow
                    key={t.id}
                    className="border-b border-edge/30 last:border-0 hover:bg-raised/30 transition-colors"
                  >
                    <TableCell className="w-32 px-4 py-2.5 text-[11px] text-faint">
                      {formatDateShort(t.executed_at)}
                    </TableCell>
                    <TableCell className="px-4 py-2.5">
                      <span className="text-xs font-medium text-bright">{t.asset_ticker}</span>
                      <span className="ml-1.5 text-[11px] text-faint">{t.exchange_code}</span>
                    </TableCell>
                    <TableCell className="px-4 py-2.5">
                      <StatusBadge value={t.side} />
                    </TableCell>
                    <TableCell className="px-4 py-2.5 text-[11px] tabular-nums text-dim">
                      {t.quantity}
                    </TableCell>
                    <TableCell className="px-4 py-2.5 text-right tabular-nums text-xs text-bright">
                      {t.total_value_home
                        ? formatCurrency(t.total_value_home, homeCurrency)
                        : formatCurrency(t.total_value, t.asset_currency_code)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </PageWrapper>
  )
}
