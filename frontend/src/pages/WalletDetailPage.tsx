import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { AxiosError } from 'axios'
import PageWrapper from '@/components/layout/PageWrapper'
import { getWallet, fxTransfer } from '@/api/wallets'
import { getFxRates } from '@/api/market'
import { formatCurrency, formatDate } from '@/lib/utils'

interface TransferForm {
  to_currency: string
  from_amount: string
}

export default function WalletDetailPage() {
  const { currencyCode } = useParams<{ currencyCode: string }>()
  const [page, setPage] = useState(1)
  const [serverError, setServerError] = useState<string | null>(null)
  const qc = useQueryClient()

  const { data: wallet, isLoading } = useQuery({
    queryKey: ['wallet', currencyCode, page],
    queryFn: () => getWallet(currencyCode!, page),
    staleTime: 5_000,
    enabled: !!currencyCode,
  })

  const { data: fxRates } = useQuery({
    queryKey: ['fx-rates'],
    queryFn: getFxRates,
    staleTime: 60_000,
  })

  const { register, handleSubmit, watch, reset, formState: { errors } } = useForm<TransferForm>()

  const toCurrency = watch('to_currency')
  const fromAmount = watch('from_amount')

  // Compute preview rate
  const previewRate = (() => {
    if (!fxRates || !currencyCode || !toCurrency || toCurrency === currencyCode) return null
    const rate = fxRates.find(r => r.from_currency === currencyCode && r.to_currency === toCurrency)
    if (!rate || !fromAmount || isNaN(parseFloat(fromAmount))) return null
    const result = parseFloat(fromAmount) * parseFloat(rate.rate)
    return result.toFixed(4)
  })()

  const transferMutation = useMutation({
    mutationFn: fxTransfer,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['wallet'] })
      qc.invalidateQueries({ queryKey: ['wallets'] })
      reset()
      setServerError(null)
    },
    onError: (err: AxiosError<{ error?: string }>) => {
      setServerError(err.response?.data?.error ?? 'Transfer failed.')
    },
  })

  const onSubmit = (formData: TransferForm) => {
    setServerError(null)
    transferMutation.mutate({
      from_currency: currencyCode!,
      to_currency: formData.to_currency,
      from_amount: formData.from_amount,
    })
  }

  // Currencies available to transfer to (all FX-rate targets from this currency)
  const availableTargets = fxRates
    ?.filter(r => r.from_currency === currencyCode)
    .map(r => r.to_currency) ?? []

  return (
    <PageWrapper title={wallet ? `${wallet.currency_name} wallet` : 'Wallet'}>
      {isLoading ? (
        <div className="flex h-40 items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-700 border-t-indigo-500" />
        </div>
      ) : wallet ? (
        <div className="space-y-6">
          {/* Balance cards */}
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <p className="mb-1 text-xs text-slate-500">Balance</p>
              <p className="text-lg font-semibold text-white">
                {formatCurrency(wallet.balance, wallet.currency_code)}
              </p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <p className="mb-1 text-xs text-slate-500">Available</p>
              <p className="text-lg font-semibold text-white">
                {formatCurrency(wallet.available_balance, wallet.currency_code)}
              </p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <p className="mb-1 text-xs text-slate-500">Reserved</p>
              <p className="text-lg font-semibold text-slate-400">
                {formatCurrency(wallet.pending_balance, wallet.currency_code)}
              </p>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            {/* FX Transfer form */}
            {availableTargets.length > 0 && (
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                <h2 className="mb-4 text-sm font-medium text-slate-300">Convert currency</h2>
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
                  <div>
                    <label className="mb-1 block text-xs text-slate-500">Amount ({currencyCode})</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0.01"
                      placeholder="0.00"
                      {...register('from_amount', {
                        required: 'Amount is required',
                        min: { value: 0.01, message: 'Must be positive' },
                      })}
                      className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-600 focus:border-indigo-500 focus:outline-none"
                    />
                    {errors.from_amount && (
                      <p className="mt-1 text-xs text-red-400">{errors.from_amount.message}</p>
                    )}
                  </div>

                  <div>
                    <label className="mb-1 block text-xs text-slate-500">To currency</label>
                    <select
                      {...register('to_currency', { required: 'Select a currency' })}
                      className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none"
                    >
                      <option value="">Select…</option>
                      {availableTargets.map(c => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                    {errors.to_currency && (
                      <p className="mt-1 text-xs text-red-400">{errors.to_currency.message}</p>
                    )}
                  </div>

                  {previewRate && toCurrency && (
                    <div className="rounded-lg bg-slate-800/50 px-3 py-2 text-xs text-slate-400">
                      ≈ {formatCurrency(previewRate, toCurrency, 4)}
                    </div>
                  )}

                  {serverError && (
                    <p className="text-xs text-red-400">{serverError}</p>
                  )}

                  <button
                    type="submit"
                    disabled={transferMutation.isPending}
                    className="w-full rounded-lg bg-indigo-600 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
                  >
                    {transferMutation.isPending ? 'Converting…' : 'Convert'}
                  </button>

                  {transferMutation.isSuccess && (
                    <p className="text-center text-xs text-emerald-400">Transfer complete!</p>
                  )}
                </form>
              </div>
            )}

            {/* Transactions */}
            <div className={availableTargets.length > 0 ? 'lg:col-span-2' : 'lg:col-span-3'}>
              <div className="rounded-xl border border-slate-800 bg-slate-900">
                <div className="border-b border-slate-800 px-4 py-3">
                  <h2 className="text-sm font-medium text-slate-300">Transactions</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-800 text-xs text-slate-500">
                        <th className="px-4 py-3 text-left">Date</th>
                        <th className="px-4 py-3 text-left">Type</th>
                        <th className="px-4 py-3 text-left">Description</th>
                        <th className="px-4 py-3 text-right">Amount</th>
                        <th className="px-4 py-3 text-right">Balance after</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(wallet.transactions.results ?? []).map((tx) => {
                        const amt = parseFloat(tx.amount)
                        const isPositive = amt >= 0
                        return (
                          <tr key={tx.id} className="border-b border-slate-800/50 last:border-0 hover:bg-slate-800/30">
                            <td className="px-4 py-2.5 text-xs text-slate-400">{formatDate(tx.timestamp)}</td>
                            <td className="px-4 py-2.5 text-xs text-slate-500">{tx.source_display}</td>
                            <td className="px-4 py-2.5 text-xs text-slate-400">{tx.description}</td>
                            <td className={`px-4 py-2.5 text-right tabular-nums text-sm font-medium ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                              {isPositive ? '+' : ''}{formatCurrency(tx.amount, wallet.currency_code)}
                            </td>
                            <td className="px-4 py-2.5 text-right tabular-nums text-slate-300">
                              {formatCurrency(tx.balance_after, wallet.currency_code)}
                            </td>
                          </tr>
                        )
                      })}
                      {wallet.transactions.results.length === 0 && (
                        <tr>
                          <td colSpan={5} className="px-4 py-8 text-center text-sm text-slate-500">
                            No transactions yet.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                {wallet.transactions.count > 25 && (
                  <div className="flex items-center justify-between border-t border-slate-800 px-4 py-3">
                    <span className="text-xs text-slate-500">{wallet.transactions.count} transactions total</span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setPage((p) => p - 1)}
                        disabled={!wallet.transactions.previous}
                        className="rounded px-3 py-1 text-xs text-slate-400 disabled:opacity-30 hover:text-white"
                      >
                        ← Prev
                      </button>
                      <button
                        onClick={() => setPage((p) => p + 1)}
                        disabled={!wallet.transactions.next}
                        className="rounded px-3 py-1 text-xs text-slate-400 disabled:opacity-30 hover:text-white"
                      >
                        Next →
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <p className="text-slate-400">Wallet not found.</p>
      )}
    </PageWrapper>
  )
}
