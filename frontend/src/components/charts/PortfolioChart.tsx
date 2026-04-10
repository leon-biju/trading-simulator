import { useState } from 'react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Filler,
} from 'chart.js'
import { useQuery } from '@tanstack/react-query'
import { getPortfolioHistory } from '@/api/trading'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Filler)

const RANGES = ['1W', '1M', '3M', '6M', '1Y', 'ALL'] as const
type Range = (typeof RANGES)[number]

export default function PortfolioChart() {
  const [range, setRange] = useState<Range>('1M')

  const { data, isLoading } = useQuery({
    queryKey: ['portfolio-history', range],
    queryFn: () => getPortfolioHistory(range),
    staleTime: 60_000,
  })

  const chartData = {
    labels: data?.labels ?? [],
    datasets: [
      {
        label: 'Total Assets',
        data: data?.datasets.total_assets ?? [],
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
        mode: 'index' as const,
        intersect: false,
        backgroundColor: '#0F1520',
        borderColor: '#1E2840',
        borderWidth: 1,
        titleColor: '#94A3B8',
        bodyColor: '#E2E8F0',
        padding: 10,
      },
    },
    scales: {
      x: {
        grid: { color: 'rgba(30,40,64,0.6)' },
        ticks: { color: '#475569', font: { size: 11, family: 'IBM Plex Sans' as const } },
        border: { color: 'transparent' },
      },
      y: {
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
        <div className="flex gap-0.5">
          {RANGES.map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`rounded px-2 py-0.5 text-xs transition ${
                range === r
                  ? 'bg-accent/15 text-accent font-medium'
                  : 'text-faint hover:text-dim'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 min-h-0">
        {isLoading ? (
          <div className="flex h-full items-center justify-center">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-edge border-t-accent" />
          </div>
        ) : !data?.labels.length ? (
          <div className="flex h-full items-center justify-center text-xs text-faint">
            No portfolio history yet
          </div>
        ) : (
          <Line data={chartData} options={options} />
        )}
      </div>
    </div>
  )
}
