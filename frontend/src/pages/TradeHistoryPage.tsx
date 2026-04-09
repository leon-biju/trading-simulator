import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import PageWrapper from '@/components/layout/PageWrapper'
import StatusBadge from '@/components/common/StatusBadge'
import { useAuth } from '@/auth/AuthContext'
import { getTrades } from '@/api/trading'
import { formatCurrency, formatDate } from '@/lib/utils'

export default function TradeHistoryPage() {
  const [page, setPage] = useState(1)
  const { user } = useAuth()
  const homeCurrency = user?.home_currency ?? 'GBP'

  const { data, isLoading } = useQuery({
    queryKey: ['trades', page],
    queryFn: () => getTrades(page),
    staleTime: 5_000,
  })

  return (
    <PageWrapper title="Trade history">
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
                  <th className="px-4 py-3 text-left">Executed</th>
                  <th className="px-4 py-3 text-left">Asset</th>
                  <th className="px-4 py-3 text-left">Side</th>
                  <th className="px-4 py-3 text-right">Qty</th>
                  <th className="px-4 py-3 text-right">Price</th>
                  <th className="px-4 py-3 text-right">Total value</th>
                  <th className="px-4 py-3 text-right">Fee</th>
                  <th className="px-4 py-3 text-right">Net amount</th>
                </tr>
              </thead>
              <tbody>
                {(data?.results ?? []).map((t) => (
                  <tr key={t.id} className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/30">
                    <td className="px-4 py-2.5 text-xs text-slate-400">{formatDate(t.executed_at)}</td>
                    <td className="px-4 py-2.5 font-medium text-white">
                      {t.asset_ticker}
                      <span className="ml-1.5 text-xs text-slate-500">{t.exchange_code}</span>
                    </td>
                    <td className="px-4 py-2.5"><StatusBadge value={t.side} /></td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-slate-300">{t.quantity}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-slate-300">
                      {t.price_home
                        ? formatCurrency(t.price_home, homeCurrency)
                        : formatCurrency(t.price, t.asset_currency_code)}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-slate-300">
                      {t.total_value_home
                        ? formatCurrency(t.total_value_home, homeCurrency)
                        : formatCurrency(t.total_value, t.asset_currency_code)}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-slate-400">
                      {t.fee_home
                        ? formatCurrency(t.fee_home, homeCurrency)
                        : formatCurrency(t.fee, t.fee_currency_code)}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-slate-300">
                      {t.net_amount_home
                        ? formatCurrency(t.net_amount_home, homeCurrency)
                        : formatCurrency(t.net_amount, t.asset_currency_code)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data && data.count > 25 && (
            <div className="flex items-center justify-between border-t border-slate-800 px-4 py-3">
              <span className="text-xs text-slate-500">{data.count} trades total</span>
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
