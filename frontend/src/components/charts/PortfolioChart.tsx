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
        borderColor: '#6366f1',
        backgroundColor: 'rgba(99,102,241,0.08)',
        borderWidth: 2,
        pointRadius: 0,
        fill: true,
        tension: 0.3,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { mode: 'index' as const, intersect: false } },
    scales: {
      x: {
        grid: { color: 'rgba(255,255,255,0.04)' },
        ticks: { color: '#64748b', font: { size: 11 } },
      },
      y: {
        grid: { color: 'rgba(255,255,255,0.04)' },
        ticks: {
          color: '#64748b',
          font: { size: 11 },
          callback: (v: unknown) =>
            `${data?.currency ?? ''} ${Number(v).toLocaleString('en-GB', { maximumFractionDigits: 0 })}`,
        },
      },
    },
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <div className="mb-4 flex items-center justify-between">
        <span className="text-sm font-medium text-slate-300">Portfolio value</span>
        <div className="flex gap-1">
          {RANGES.map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`rounded px-2 py-0.5 text-xs transition ${
                range === r
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>
      <div className="h-48">
        {isLoading ? (
          <div className="flex h-full items-center justify-center">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-700 border-t-indigo-500" />
          </div>
        ) : !data?.labels.length ? (
          <div className="flex h-full items-center justify-center text-sm text-slate-500">
            No portfolio history yet
          </div>
        ) : (
          <Line data={chartData} options={options} />
        )}
      </div>
    </div>
  )
}
