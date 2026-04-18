import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Trophy } from 'lucide-react'
import PageWrapper from '@/components/layout/PageWrapper'
import { usePageTitle } from '@/hooks/usePageTitle'
import { useAuth } from '@/auth/AuthContext'
import { getLeaderboard, type LeaderboardPeriod } from '@/api/leaderboard'
import { Skeleton } from '@/components/ui/skeleton'
import { pnlClass } from '@/lib/utils'

const PERIODS: { id: LeaderboardPeriod; label: string }[] = [
  { id: 'today', label: 'Today' },
  { id: 'week',  label: 'This week' },
  { id: 'month', label: 'This month' },
  { id: 'year',  label: 'This year' },
]

const MEDAL: Record<number, string> = { 1: 'text-yellow-400', 2: 'text-slate-400', 3: 'text-amber-600' }

export default function LeaderboardPage() {
  usePageTitle('Leaderboard')
  const { user } = useAuth()
  const [period, setPeriod] = useState<LeaderboardPeriod>('week')

  const { data, isLoading } = useQuery({
    queryKey: ['leaderboard', period],
    queryFn: () => getLeaderboard(period),
    staleTime: 60_000,
  })

  const tabCls = (id: LeaderboardPeriod) =>
    `px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
      period === id
        ? 'border-brand text-brand'
        : 'border-transparent text-faint hover:text-dim'
    }`

  return (
    <PageWrapper>
      <div className="mb-6 flex items-center gap-3">
        <Trophy className="size-5 text-faint" />
        <h1 className="text-2xl font-semibold text-bright">Leaderboard</h1>
      </div>

      <div className="mb-6 flex border-b border-edge">
        {PERIODS.map(({ id, label }) => (
          <button key={id} onClick={() => setPeriod(id)} className={tabCls(id)}>
            {label}
          </button>
        ))}
      </div>

      <div className="rounded-lg border border-edge bg-panel overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-edge text-[11px] uppercase tracking-wider text-faint">
              <th className="px-4 py-3 text-left font-medium w-12">#</th>
              <th className="px-4 py-3 text-left font-medium">User</th>
              <th className="px-4 py-3 text-right font-medium">Portfolio value</th>
              <th className="px-4 py-3 text-right font-medium">Return ($)</th>
              <th className="px-4 py-3 text-right font-medium">Return (%)</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              Array.from({ length: 10 }).map((_, i) => (
                <tr key={i} className="border-b border-edge/40 last:border-0">
                  <td className="px-4 py-3"><Skeleton className="h-4 w-6" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-28" /></td>
                  <td className="px-4 py-3 text-right"><Skeleton className="h-4 w-24 ml-auto" /></td>
                  <td className="px-4 py-3 text-right"><Skeleton className="h-4 w-20 ml-auto" /></td>
                  <td className="px-4 py-3 text-right"><Skeleton className="h-4 w-16 ml-auto" /></td>
                </tr>
              ))
            ) : !data?.length ? (
              <tr>
                <td colSpan={5} className="px-4 py-16 text-center text-sm text-faint">
                  No data yet for this period.
                </td>
              </tr>
            ) : (
              data.map((entry) => {
                const isMe = user?.username === entry.username
                const returnPct = parseFloat(entry.return_pct)
                const returnAbs = parseFloat(entry.return_abs)
                const medalCls = MEDAL[entry.rank]

                return (
                  <tr
                    key={entry.rank}
                    className={`border-b border-edge/40 last:border-0 transition-colors ${
                      isMe ? 'bg-brand/5' : 'hover:bg-raised/40'
                    }`}
                  >
                    <td className="px-4 py-3">
                      {medalCls ? (
                        <Trophy className={`size-4 ${medalCls}`} />
                      ) : (
                        <span className="text-xs tabular-nums text-faint">{entry.rank}</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-sm font-medium ${isMe ? 'text-brand' : 'text-bright'}`}>
                        {entry.username}
                      </span>
                      {isMe && (
                        <span className="ml-2 text-[10px] uppercase tracking-wide text-brand/70 font-semibold">you</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-xs text-dim">
                      {parseFloat(entry.current_total).toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className={`px-4 py-3 text-right tabular-nums text-xs ${pnlClass(returnAbs)}`}>
                      {returnAbs >= 0 ? '+' : ''}{returnAbs.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className={`px-4 py-3 text-right tabular-nums text-xs font-medium ${pnlClass(returnPct)}`}>
                      {returnPct >= 0 ? '+' : ''}{returnPct.toFixed(2)}%
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </PageWrapper>
  )
}
