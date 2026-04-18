import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getWatchlist, addToWatchlist, removeFromWatchlist } from '@/api/market'
import { useAuth } from '@/auth/AuthContext'

export function useWatchlist() {
  const { isAuthenticated } = useAuth()
  const qc = useQueryClient()

  const { data: watchlist = [] } = useQuery({
    queryKey: ['watchlist'],
    queryFn: getWatchlist,
    staleTime: 30_000,
    enabled: isAuthenticated,
  })

  const addMutation = useMutation({
    mutationFn: ({ exchangeCode, ticker }: { exchangeCode: string; ticker: string }) =>
      addToWatchlist(exchangeCode, ticker),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
  })

  const removeMutation = useMutation({
    mutationFn: ({ exchangeCode, ticker }: { exchangeCode: string; ticker: string }) =>
      removeFromWatchlist(exchangeCode, ticker),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
  })

  function isWatched(exchangeCode: string, ticker: string) {
    return watchlist.some(
      w => w.exchange_code === exchangeCode && w.ticker === ticker,
    )
  }

  function toggleWatch(exchangeCode: string, ticker: string) {
    if (isWatched(exchangeCode, ticker)) {
      removeMutation.mutate({ exchangeCode, ticker })
    } else {
      addMutation.mutate({ exchangeCode, ticker })
    }
  }

  const isPending = addMutation.isPending || removeMutation.isPending

  return { watchlist, isWatched, toggleWatch, isPending }
}
