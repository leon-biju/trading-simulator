import api from '@/lib/axios'

export type LeaderboardPeriod = 'today' | 'week' | 'month' | 'year'

export interface LeaderboardEntry {
  rank: number
  username: string
  current_total: string
  return_abs: string
  return_pct: string
}

export async function getLeaderboard(
  period: LeaderboardPeriod = 'week',
  limit = 50,
): Promise<LeaderboardEntry[]> {
  const { data } = await api.get<LeaderboardEntry[]>('/api/leaderboard/', {
    params: { period, limit },
  })
  return data
}
