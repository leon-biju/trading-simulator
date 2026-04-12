import { useState } from 'react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Filler,
  type TooltipItem,
} from 'chart.js'
import { useQuery } from '@tanstack/react-query'
import { getPortfolioHistory } from '@/api/trading'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { Skeleton } from '@/components/ui/skeleton'

ChartJS.register(LinearScale, PointElement, LineElement, Tooltip, Filler)

// Parse "YYYY-MM-DD" in local time to avoid UTC midnight off-by-one issues
function parseISODate(iso: string): number {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).getTime()
}

function formatDateTick(ts: number, range: string): string {
  const d = new Date(ts)
  const day = d.getDate()
  const month = d.toLocaleString('en-GB', { month: 'short' })
  const year = d.getFullYear()
  if (range === '1W' || range === '1M' || range === '3M') return `${day} ${month}`
  return `${month} '${String(year).slice(2)}`
}

const RANGE_MS: Record<string, number | null> = {
  '1W': 7 * 86_400_000,
  '1M': 30 * 86_400_000,
  '3M': 90 * 86_400_000,
  '6M': 180 * 86_400_000,
  '1Y': 365 * 86_400_000,
  'ALL': null,
}

const RANGES = ['1W', '1M', '3M', '6M', '1Y', 'ALL'] as const
type Range = (typeof RANGES)[number]

export default function PortfolioChart() {
  const [range, setRange] = useState<Range>('1M')

  const { data, isLoading } = useQuery({
    queryKey: ['portfolio-history', range],
    queryFn: () => getPortfolioHistory(range),
    staleTime: 60_000,
  })

  const now = Date.now()

  const points =
    data?.labels.map((iso, i) => ({
      x: parseISODate(iso),
      y: data.datasets.total_assets[i],
    })) ?? []

  const windowMs = RANGE_MS[range]
  const xMin = windowMs !== null
    ? now - windowMs
    : (points[0]?.x ?? now - 30 * 86_400_000)
  const xMax = now

  const yValues = points.map(p => p.y)
  const yMin = yValues.length ? Math.min(...yValues) : 0
  const yMax = yValues.length ? Math.max(...yValues) : 100
  const yPad = (yMax - yMin) * 0.05 || yMax * 0.1 || 1
  const yScaleMin = Math.max(0, yMin - yPad)
  const yScaleMax = yMax + yPad

  const chartData = {
    datasets: [
      {
        label: 'Total Assets',
        data: points,
        parsing: false as const,
        borderColor: '#06B6D4',
        backgroundColor: 'rgba(6,182,212,0.06)',
        borderWidth: 1.5,
        pointRadius: 0,
        fill: true,
        tension: 0,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        mode: 'nearest' as const,
        intersect: false,
        backgroundColor: '#0F1520',
        borderColor: '#1E2840',
        borderWidth: 1,
        titleColor: '#94A3B8',
        bodyColor: '#E2E8F0',
        padding: 10,
        callbacks: {
          title: (items: TooltipItem<'line'>[]) => {
            if (!items.length) return ''
            const x = items[0].parsed.x
            if (x == null) return ''
            const d = new Date(x)
            return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
          },
        },
      },
    },
    scales: {
      x: {
        type: 'linear' as const,
        min: xMin,
        max: xMax,
        grid: { color: 'rgba(30,40,64,0.6)' },
        ticks: {
          color: '#475569',
          font: { size: 11, family: 'IBM Plex Sans' as const },
          maxTicksLimit: 6,
          callback: (v: unknown) => formatDateTick(Number(v), range),
        },
        border: { color: 'transparent' },
      },
      y: {
        min: yScaleMin,
        max: yScaleMax,
        grid: { color: 'rgba(30,40,64,0.6)' },
        ticks: {
          color: '#475569',
          font: { size: 11, family: 'IBM Plex Sans' as const },
          callback: (v: unknown) =>
            data?.currency + ' ' + Number(v).toLocaleString('en-GB', { maximumFractionDigits: 0 }),
        },
        border: { color: 'transparent' },
      },
    },
  }

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-[11px] font-medium text-faint uppercase tracking-wider">Portfolio value</span>
        <ToggleGroup
          type="single"
          value={range}
          onValueChange={(v) => v && setRange(v as Range)}
          className="gap-0"
        >
          {RANGES.map((r) => (
            <ToggleGroupItem
              key={r}
              value={r}
              className="h-6 px-2 text-xs font-medium text-faint rounded data-[state=on]:bg-brand/15 data-[state=on]:text-brand hover:text-dim hover:bg-transparent"
            >
              {r}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </div>
      <div className="flex-1 min-h-0">
        {isLoading ? (
          <Skeleton className="h-full w-full" />
        ) : !data?.labels.length ? (
          <div className="flex h-full items-center justify-center text-xs text-faint">
            No portfolio history yet
          </div>
        ) : (
          <Line key={range} data={chartData} options={options} />
        )}
      </div>
    </div>
  )
}
