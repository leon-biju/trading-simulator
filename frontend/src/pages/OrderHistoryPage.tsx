import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import PageWrapper from '@/components/layout/PageWrapper'
import StatusBadge from '@/components/common/StatusBadge'
import { getOrders, cancelOrder } from '@/api/trading'
import { formatDate } from '@/lib/utils'

export default function OrderHistoryPage() {
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

  return (
    <PageWrapper title="Order history">
      {isLoading ? (
        <div className="flex h-40 items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-700 border-t-indigo-500" />
        </div>
      ) : (
        <div className="rounded-xl border border-slate-800 bg-slate-900">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs text-slate-500">
                  <th className="px-4 py-3 text-left">Date</th>
                  <th className="px-4 py-3 text-left">Asset</th>
                  <th className="px-4 py-3 text-left">Side</th>
                  <th className="px-4 py-3 text-left">Type</th>
                  <th className="px-4 py-3 text-right">Qty</th>
                  <th className="px-4 py-3 text-right">Limit price</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {(data?.results ?? []).map((o) => (
                  <tr key={o.id} className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/30">
                    <td className="px-4 py-2.5 text-xs text-slate-400">{formatDate(o.created_at)}</td>
                    <td className="px-4 py-2.5 font-medium text-white">
                      {o.asset_ticker}
                      <span className="ml-1.5 text-xs text-slate-500">{o.exchange_code}</span>
                    </td>
                    <td className="px-4 py-2.5"><StatusBadge value={o.side} /></td>
                    <td className="px-4 py-2.5 text-xs text-slate-400">{o.order_type}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-slate-300">{o.quantity}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-slate-400">
                      {o.limit_price ?? '—'}
                    </td>
                    <td className="px-4 py-2.5"><StatusBadge value={o.status} /></td>
                    <td className="px-4 py-2.5 text-right">
                      {o.status === 'PENDING' && (
                        <button
                          onClick={() => cancelMutation.mutate(o.id)}
                          disabled={cancelMutation.isPending}
                          className="text-xs text-red-400 hover:text-red-300 disabled:opacity-50"
                        >
                          Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data && data.count > 25 && (
            <div className="flex items-center justify-between border-t border-slate-800 px-4 py-3">
              <span className="text-xs text-slate-500">
                {data.count} orders total
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => p - 1)}
                  disabled={!data.previous}
                  className="rounded px-3 py-1 text-xs text-slate-400 disabled:opacity-30 hover:text-white"
                >
                  ← Prev
                </button>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={!data.next}
                  className="rounded px-3 py-1 text-xs text-slate-400 disabled:opacity-30 hover:text-white"
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </PageWrapper>
  )
}
