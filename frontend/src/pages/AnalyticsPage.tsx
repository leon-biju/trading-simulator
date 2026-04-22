import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Chart as ChartJS,
  ArcElement,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  type TooltipItem,
} from 'chart.js'
import { Doughnut, Bar } from 'react-chartjs-2'
import { BarChart3, Activity } from 'lucide-react'
import PageWrapper from '@/components/layout/PageWrapper'
import PortfolioChart from '@/components/charts/PortfolioChart'
import StatCard from '@/components/common/StatCard'
import EmptyState from '@/components/common/EmptyState'
import { usePageTitle } from '@/hooks/usePageTitle'
import { useAuth } from '@/auth/AuthContext'
import {
  getPortfolio,
  getAnalyticsStats,
  getAnalyticsAllocation,
  getAnalyticsActivity,
} from '@/api/trading'
import { formatCurrency, formatPercent, pnlClass } from '@/lib/utils'
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

ChartJS.register(ArcElement, BarElement, CategoryScale, LinearScale, Tooltip)

/* ── Colour palette for allocation donut ─────────────────────── */

const CURRENCY_COLORS: Record<string, string> = {
  GBP: '#06B6D4',
  USD: '#10B981',
  EUR: '#F59E0B',
  JPY: '#8B5CF6',
  CAD: '#F97316',
  AUD: '#EC4899',
  CHF: '#3B82F6',
  HKD: '#14B8A6',
}
const FALLBACK_COLORS = ['#6366F1', '#84CC16', '#F43F5E', '#0EA5E9', '#A78BFA']

function currencyColor(code: string, index: number): string {
  return CURRENCY_COLORS[code] ?? FALLBACK_COLORS[index % FALLBACK_COLORS.length]
}

/* ── Helpers ─────────────────────────────────────────────────── */

function SectionHeader({ title }: { title: string }) {
  return (
    <h2 className="text-xs font-semibold uppercase tracking-widest text-faint mb-3">
      {title}
    </h2>
  )
}

function CardSkeleton({ height = 'h-32' }: { height?: string }) {
  return <Skeleton className={`w-full rounded-lg ${height}`} />
}

/* ── Allocation donut ─────────────────────────────────────────── */

function AllocationSection() {
  const { user } = useAuth()
  const homeCurrency = user?.home_currency ?? 'GBP'

  const { data, isLoading } = useQuery({
    queryKey: ['analytics-allocation'],
    queryFn: getAnalyticsAllocation,
    staleTime: 60_000,
  })

  const colors = useMemo(
    () => (data?.allocations ?? []).map((a, i) => currencyColor(a.currency, i)),
    [data],
  )

  if (isLoading) return <CardSkeleton height="h-72" />

  const allocations = data?.allocations ?? []

  if (!allocations.length) {
    return (
      <Card className="bg-panel border-edge">
        <CardContent className="py-8">
          <EmptyState icon={BarChart3} title="No allocation data" description="Start trading to see your allocation" />
        </CardContent>
      </Card>
    )
  }

  const chartData = {
    labels: allocations.map(a => a.currency),
    datasets: [
      {
        data: allocations.map(a => a.total_home),
        backgroundColor: colors.map(c => c + '33'),
        borderColor: colors,
        borderWidth: 1.5,
        hoverBackgroundColor: colors.map(c => c + '55'),
      },
    ],
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '72%',
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#0F1520',
        borderColor: '#1E2840',
        borderWidth: 1,
        titleColor: '#94A3B8',
        bodyColor: '#E2E8F0',
        padding: 10,
        callbacks: {
          label: (item: TooltipItem<'doughnut'>) => {
            const a = allocations[item.dataIndex]
            return ` ${a.percent.toFixed(1)}% · ${formatCurrency(a.total_home, homeCurrency)}`
          },
        },
      },
    },
  }

  return (
    <Card className="bg-panel border-edge">
      <CardHeader className="px-4 pt-4 pb-0">
        <CardTitle className="text-sm font-medium text-bright">By Currency</CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        <div className="flex gap-6 items-center mt-3">
          <div className="relative h-36 w-36 shrink-0">
            <Doughnut data={chartData} options={chartOptions} />
          </div>
          <div className="flex-1 min-w-0 space-y-2">
            {allocations.map((a, i) => (
              <div key={a.currency} className="flex items-center gap-2">
                <span
                  className="h-2 w-2 rounded-full shrink-0"
                  style={{ backgroundColor: colors[i] }}
                />
                <span className="text-xs font-medium text-dim w-8 shrink-0">{a.currency}</span>
                <div className="flex-1 min-w-0">
                  <div className="h-1 rounded-full bg-raised overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${a.percent}%`, backgroundColor: colors[i] + '99' }}
                    />
                  </div>
                </div>
                <span className="text-[11px] tabular-nums text-faint shrink-0 w-10 text-right">
                  {a.percent.toFixed(1)}%
                </span>
              </div>
            ))}
            <div className="pt-2 border-t border-edge mt-2 space-y-1">
              {allocations.map((a, i) => (
                <div key={a.currency} className="flex justify-between text-[11px]">
                  <span className="text-faint flex items-center gap-1.5">
                    <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: colors[i] }} />
                    {a.currency} invested
                  </span>
                  <span className="tabular-nums text-dim">{formatCurrency(a.invested_home, homeCurrency)}</span>
                </div>
              ))}
              {allocations.map((a, i) => (
                a.cash_home > 0 && (
                  <div key={`${a.currency}-cash`} className="flex justify-between text-[11px]">
                    <span className="text-faint flex items-center gap-1.5">
                      <span className="h-1.5 w-1.5 rounded-full opacity-40" style={{ backgroundColor: colors[i] }} />
                      {a.currency} cash
                    </span>
                    <span className="tabular-nums text-dim">{formatCurrency(a.cash_home, homeCurrency)}</span>
                  </div>
                )
              ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

/* ── Per-asset P&L table ─────────────────────────────────────── */

function AssetPnlTable() {
  const { user } = useAuth()
  const homeCurrency = user?.home_currency ?? 'GBP'

  const { data: portfolio, isLoading } = useQuery({
    queryKey: ['portfolio'],
    queryFn: getPortfolio,
    staleTime: 30_000,
  })

  const sorted = useMemo(() => {
    const positions = portfolio?.positions ?? []
    return [...positions].sort((a, b) => {
      const totalA = (parseFloat(a.realized_pnl_home ?? '0') || 0) + (parseFloat(a.unrealized_pnl_home ?? '0') || 0)
      const totalB = (parseFloat(b.realized_pnl_home ?? '0') || 0) + (parseFloat(b.unrealized_pnl_home ?? '0') || 0)
      return totalB - totalA
    })
  }, [portfolio])

  const best = useMemo(() => {
    const traded = (portfolio?.positions ?? []).filter(p => parseFloat(p.realized_pnl) !== 0)
    if (!traded.length) return null
    return traded.reduce((a, b) =>
      parseFloat(a.realized_pnl_home ?? '0') > parseFloat(b.realized_pnl_home ?? '0') ? a : b,
    )
  }, [portfolio])

  const worst = useMemo(() => {
    const traded = (portfolio?.positions ?? []).filter(p => parseFloat(p.realized_pnl) !== 0)
    if (!traded.length) return null
    return traded.reduce((a, b) =>
      parseFloat(a.realized_pnl_home ?? '0') < parseFloat(b.realized_pnl_home ?? '0') ? a : b,
    )
  }, [portfolio])

  if (isLoading) return <CardSkeleton height="h-64" />

  return (
    <div className="space-y-3">
      {(best || worst) && (
        <div className="grid grid-cols-2 gap-3">
          {best && (
            <Card className="bg-panel border-edge">
              <CardContent className="px-3 py-2.5">
                <p className="text-[10px] uppercase tracking-wider text-faint mb-1">Best Position</p>
                <p className="text-sm font-semibold text-bright">{best.asset_ticker}</p>
                <p className={`text-xs tabular-nums mt-0.5 ${pnlClass(best.realized_pnl_home)}`}>
                  {formatCurrency(best.realized_pnl_home, homeCurrency)} realized
                </p>
              </CardContent>
            </Card>
          )}
          {worst && worst.asset_ticker !== best?.asset_ticker && (
            <Card className="bg-panel border-edge">
              <CardContent className="px-3 py-2.5">
                <p className="text-[10px] uppercase tracking-wider text-faint mb-1">Worst Position</p>
                <p className="text-sm font-semibold text-bright">{worst.asset_ticker}</p>
                <p className={`text-xs tabular-nums mt-0.5 ${pnlClass(worst.realized_pnl_home)}`}>
                  {formatCurrency(worst.realized_pnl_home, homeCurrency)} realized
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      <Card className="bg-panel border-edge">
        <CardHeader className="px-4 pt-4 pb-0">
          <CardTitle className="text-sm font-medium text-bright">Holdings P&amp;L</CardTitle>
        </CardHeader>
        <CardContent className="px-0 pb-0">
          {!sorted.length ? (
            <div className="px-4 py-6">
              <EmptyState icon={BarChart3} title="No positions" description="Buy assets to see P&L breakdown" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-edge hover:bg-transparent">
                  <TableHead className="text-[11px] uppercase tracking-wider text-faint pl-4">Asset</TableHead>
                  <TableHead className="text-[11px] uppercase tracking-wider text-faint text-right">Realized</TableHead>
                  <TableHead className="text-[11px] uppercase tracking-wider text-faint text-right">Unrealized</TableHead>
                  <TableHead className="text-[11px] uppercase tracking-wider text-faint text-right pr-4">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sorted.map(pos => {
                  const realized = parseFloat(pos.realized_pnl_home ?? '0') || 0
                  const unrealized = parseFloat(pos.unrealized_pnl_home ?? '0') || 0
                  const total = realized + unrealized
                  return (
                    <TableRow key={pos.id} className="border-edge hover:bg-raised/50">
                      <TableCell className="pl-4 py-2.5">
                        <p className="text-sm font-medium text-bright">{pos.asset_ticker}</p>
                        <p className="text-[11px] text-faint">{pos.exchange_code}</p>
                      </TableCell>
                      <TableCell className={`text-right text-xs tabular-nums ${pnlClass(realized)}`}>
                        {realized !== 0 ? formatCurrency(realized, homeCurrency) : '—'}
                      </TableCell>
                      <TableCell className={`text-right text-xs tabular-nums ${pnlClass(unrealized)}`}>
                        {pos.unrealized_pnl_home != null ? formatCurrency(unrealized, homeCurrency) : '—'}
                      </TableCell>
                      <TableCell className={`text-right text-xs tabular-nums pr-4 font-medium ${pnlClass(total)}`}>
                        {formatCurrency(total, homeCurrency)}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

/* ── Activity bar chart ───────────────────────────────────────── */

function ActivityChart() {
  const { data, isLoading } = useQuery({
    queryKey: ['analytics-activity'],
    queryFn: getAnalyticsActivity,
    staleTime: 60_000,
  })

  if (isLoading) return <CardSkeleton height="h-48" />

  const activity = data ?? []

  if (!activity.length) {
    return (
      <Card className="bg-panel border-edge">
        <CardContent className="py-8">
          <EmptyState icon={Activity} title="No trading activity yet" description="Your trade history will appear here" />
        </CardContent>
      </Card>
    )
  }

  const labels = activity.map(e => {
    const [y, m, d] = e.week.split('-').map(Number)
    const date = new Date(y, m - 1, d)
    return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
  })

  const chartData = {
    labels,
    datasets: [
      {
        label: 'Trades',
        data: activity.map(e => e.count),
        backgroundColor: 'rgba(6,182,212,0.25)',
        borderColor: '#06B6D4',
        borderWidth: 1,
        borderRadius: 3,
      },
    ],
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#0F1520',
        borderColor: '#1E2840',
        borderWidth: 1,
        titleColor: '#94A3B8',
        bodyColor: '#E2E8F0',
        padding: 10,
        callbacks: {
          title: (items: TooltipItem<'bar'>[]) => `Week of ${items[0]?.label ?? ''}`,
          label: (item: TooltipItem<'bar'>) => ` ${item.parsed.y} trade${item.parsed.y !== 1 ? 's' : ''}`,
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: {
          color: '#475569',
          font: { size: 11, family: 'IBM Plex Sans' as const },
          maxTicksLimit: 12,
          maxRotation: 0,
        },
        border: { color: 'transparent' },
      },
      y: {
        beginAtZero: true,
        grid: { color: 'rgba(30,40,64,0.3)' },
        ticks: {
          color: '#475569',
          font: { size: 11, family: 'IBM Plex Sans' as const },
          stepSize: 1,
          maxTicksLimit: 5,
        },
        border: { color: 'transparent' },
      },
    },
  }

  return (
    <Card className="bg-panel border-edge">
      <CardContent className="px-4 pt-4 pb-3">
        <div className="h-40">
          <Bar data={chartData} options={chartOptions} />
        </div>
      </CardContent>
    </Card>
  )
}

/* ── Stats cards ─────────────────────────────────────────────── */

function StatsRow() {
  const { user } = useAuth()
  const homeCurrency = user?.home_currency ?? 'GBP'

  const { data, isLoading } = useQuery({
    queryKey: ['analytics-stats'],
    queryFn: getAnalyticsStats,
    staleTime: 60_000,
  })

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[...Array(4)].map((_, i) => <CardSkeleton key={i} height="h-20" />)}
      </div>
    )
  }

  const winRateLabel = data?.win_rate != null
    ? `${data.winning_positions}/${data.total_traded_positions} positions`
    : 'No closed positions'

  const drawdownLabel = data?.max_drawdown_pct != null && data.max_drawdown_pct > 0
    ? `peak-to-trough`
    : undefined

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <StatCard
        label="Total Trades"
        value={data?.total_trades ?? 0}
      />
      <StatCard
        label="Win Rate"
        value={data?.win_rate != null ? `${data.win_rate.toFixed(1)}%` : '—'}
        subvalue={winRateLabel}
        trend={
          data?.win_rate != null
            ? { direction: data.win_rate >= 50 ? 'up' : 'down', label: `${data.win_rate.toFixed(0)}%` }
            : undefined
        }
      />
      <StatCard
        label="Max Drawdown"
        value={data?.max_drawdown_pct != null ? formatPercent(-data.max_drawdown_pct) : '—'}
        subvalue={drawdownLabel}
        trend={
          data?.max_drawdown_pct != null && data.max_drawdown_pct > 0
            ? { direction: 'down', label: `${data.max_drawdown_pct.toFixed(1)}%` }
            : undefined
        }
      />
      <StatCard
        label="Total Fees Paid"
        value={formatCurrency(data?.total_fees_home ?? 0, homeCurrency)}
        trend={
          data?.total_fees_home && data.total_fees_home > 0
            ? { direction: 'neutral', label: 'lifetime' }
            : undefined
        }
      />
    </div>
  )
}

/* ── Page ────────────────────────────────────────────────────── */

export default function AnalyticsPage() {
  usePageTitle('Analytics')

  return (
    <PageWrapper>
      <div className="space-y-8 p-4 sm:p-6 max-w-[1400px] mx-auto">

        {/* Header */}
        <div>
          <h1 className="text-xl font-semibold text-bright">Analytics</h1>
          <p className="text-sm text-faint mt-0.5">Personal performance breakdown</p>
        </div>

        {/* Portfolio chart */}
        <section>
          <SectionHeader title="Portfolio Performance" />
          <Card className="bg-panel border-edge">
            <CardContent className="px-4 pt-4 pb-3">
              <div className="h-56">
                <PortfolioChart />
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Key metrics */}
        <section>
          <SectionHeader title="Key Metrics" />
          <StatsRow />
        </section>

        {/* Allocation + P&L table */}
        <section>
          <SectionHeader title="Allocation &amp; Holdings" />
          <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4">
            <AllocationSection />
            <AssetPnlTable />
          </div>
        </section>

        {/* Activity */}
        <section>
          <SectionHeader title="Trading Activity" />
          <div className="mb-1 flex items-center justify-between">
            <p className="text-xs text-faint">Trades per week</p>
          </div>
          <ActivityChart />
        </section>

      </div>
    </PageWrapper>
  )
}
