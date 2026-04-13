import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { AxiosError } from 'axios'
import PageWrapper from '@/components/layout/PageWrapper'
import { getWallet, getWallets, fxTransfer } from '@/api/wallets'
import { getFxRates } from '@/api/market'
import { formatCurrency, formatDate } from '@/lib/utils'

interface AddFundsForm {
  from_currency: string
  to_amount: string
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

  const { data: allWallets } = useQuery({
    queryKey: ['wallets'],
    queryFn: getWallets,
    staleTime: 10_000,
  })

  const { register, handleSubmit, watch, reset, formState: { errors } } = useForm<AddFundsForm>()
  const fromCurrency = watch('from_currency')
  const toAmount = watch('to_amount')

  // Estimate how much will be deducted from the source wallet.
  // All stored rates are base→target (e.g. USD→X), so cross-rates are toRate/fromRate,
  // matching Django's get_fx_rate logic. Base currency itself has no entry (implicit rate = 1).
  const previewDeduction = (() => {
    if (!fxRates || !fromCurrency || !toAmount || isNaN(parseFloat(toAmount))) return null
    const amt = parseFloat(toAmount)
    const fromEntry = fxRates.find(r => r.to_currency === fromCurrency)
    const toEntry   = fxRates.find(r => r.to_currency === currencyCode)
    const fromBaseRate = fromEntry ? parseFloat(fromEntry.rate) : 1.0
    const toBaseRate   = toEntry   ? parseFloat(toEntry.rate)   : 1.0
    // from_amount = to_amount / (toBaseRate / fromBaseRate)
    const raw = amt * fromBaseRate / toBaseRate
    return (Math.round(raw * 100) / 100).toFixed(2)
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

  const onSubmit = (formData: AddFundsForm) => {
    setServerError(null)
    transferMutation.mutate({
      from_currency: formData.from_currency,
      to_currency: currencyCode!,
      to_amount: formData.to_amount,
    })
  }

  const otherWallets = allWallets?.filter(w => w.currency_code !== currencyCode) ?? []

  const inputCls = 'w-full rounded border border-edge bg-raised px-3 py-2 text-sm text-bright placeholder-faint focus:border-brand focus:outline-none transition-colors'

  return (
    <PageWrapper>
      {isLoading ? (
        <div className="flex h-40 items-center justify-center">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-edge border-t-accent" />
        </div>
      ) : wallet ? (
        <div>
          {/* Header */}
          <h1 className="mb-5 text-lg font-semibold text-bright">
            {wallet.currency_name}
            <span className="ml-2 text-sm font-normal text-faint">{wallet.currency_code}</span>
          </h1>

          {/* Balance cards */}
          <div className="mb-5 grid grid-cols-3 gap-3">
            {[
              { label: 'Balance',   value: formatCurrency(wallet.balance,           wallet.currency_code) },
              { label: 'Available', value: formatCurrency(wallet.available_balance,  wallet.currency_code) },
              { label: 'Reserved',  value: formatCurrency(wallet.pending_balance,   wallet.currency_code) },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-lg border border-edge bg-panel px-4 py-3">
                <p className="mb-1 text-[11px] uppercase tracking-wider text-faint">{label}</p>
                <p className="text-base font-semibold tabular-nums text-bright">{value}</p>
              </div>
            ))}
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            {/* Add Funds */}
            {otherWallets.length > 0 && (
              <div className="rounded-lg border border-edge bg-panel p-4">
                <h2 className="mb-4 text-[11px] uppercase tracking-wider text-faint">Add funds</h2>
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
                  <div>
                    <label className="mb-1 block text-[11px] uppercase tracking-wider text-faint">From wallet</label>
                    <select
                      {...register('from_currency', { required: 'Select a wallet' })}
                      className={inputCls}
                    >
                      <option value="">Select…</option>
                      {otherWallets.map(w => (
                        <option key={w.currency_code} value={w.currency_code}>
                          {w.currency_code} ({formatCurrency(w.available_balance, w.currency_code)} available)
                        </option>
                      ))}
                    </select>
                    {errors.from_currency && <p className="mt-1 text-xs text-sell">{errors.from_currency.message}</p>}
                  </div>

                  <div>
                    <label className="mb-1 block text-[11px] uppercase tracking-wider text-faint">
                      Amount to add ({currencyCode})
                    </label>
                    <input
                      type="number" step="0.01" min="0.01" placeholder="0.00"
                      {...register('to_amount', {
                        required: 'Amount is required',
                        min: { value: 0.01, message: 'Must be positive' },
                      })}
                      className={inputCls}
                    />
                    {errors.to_amount && <p className="mt-1 text-xs text-sell">{errors.to_amount.message}</p>}
                  </div>

                  {previewDeduction && fromCurrency && (
                    <div className="rounded border border-edge/50 bg-raised px-3 py-2 text-[11px] text-dim">
                      ≈ <span className="tabular-nums text-bright">{formatCurrency(previewDeduction, fromCurrency)}</span>
                      <span className="ml-1">deducted from {fromCurrency} wallet</span>
                    </div>
                  )}

                  {serverError && <p className="text-xs text-sell">{serverError}</p>}

                  <button
                    type="submit"
                    disabled={transferMutation.isPending}
                    className="w-full rounded bg-brand py-2 text-sm font-medium text-base transition hover:bg-brand/90 disabled:opacity-50"
                  >
                    {transferMutation.isPending ? 'Adding…' : 'Add funds'}
                  </button>

                  {transferMutation.isSuccess && (
                    <p className="text-center text-xs text-buy">Transfer complete!</p>
                  )}
                </form>
              </div>
            )}

            {/* Transactions */}
            <div className={otherWallets.length > 0 ? 'lg:col-span-2' : 'lg:col-span-3'}>
              <div className="rounded-lg border border-edge bg-panel">
                <div className="border-b border-edge px-4 py-3">
                  <h2 className="text-[11px] uppercase tracking-wider text-faint">Transactions</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-edge/60 text-[11px] uppercase tracking-wider text-faint">
                        <th className="px-4 py-2.5 text-left font-medium">Date</th>
                        <th className="px-4 py-2.5 text-left font-medium">Type</th>
                        <th className="px-4 py-2.5 text-left font-medium hidden md:table-cell">Description</th>
                        <th className="px-4 py-2.5 text-right font-medium">Amount</th>
                        <th className="px-4 py-2.5 text-right font-medium hidden sm:table-cell">Balance after</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(wallet.transactions.results ?? []).map((tx) => {
                        const amt = parseFloat(tx.amount)
                        const pos = amt >= 0
                        return (
                          <tr key={tx.id} className="border-b border-edge/40 last:border-0 hover:bg-raised/40 transition-colors">
                            <td className="px-4 py-2.5 text-[11px] text-faint">{formatDate(tx.timestamp)}</td>
                            <td className="px-4 py-2.5 text-[11px] text-faint">{tx.source_display}</td>
                            <td className="px-4 py-2.5 text-xs text-dim hidden md:table-cell">{tx.description}</td>
                            <td className={`px-4 py-2.5 text-right tabular-nums text-sm font-medium ${pos ? 'text-buy' : 'text-sell'}`}>
                              {pos ? '+' : ''}{formatCurrency(tx.amount, wallet.currency_code)}
                            </td>
                            <td className="px-4 py-2.5 text-right tabular-nums text-xs text-dim hidden sm:table-cell">
                              {formatCurrency(tx.balance_after, wallet.currency_code)}
                            </td>
                          </tr>
                        )
                      })}
                      {wallet.transactions.results.length === 0 && (
                        <tr>
                          <td colSpan={5} className="px-4 py-12 text-center text-sm text-faint">No transactions yet</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                {wallet.transactions.count > 25 && (
                  <div className="flex items-center justify-between border-t border-edge px-4 py-3">
                    <span className="text-[11px] text-faint">{wallet.transactions.count} transactions total</span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setPage(p => p - 1)} disabled={!wallet.transactions.previous}
                        className="rounded px-3 py-1 text-xs text-dim disabled:opacity-30 hover:text-bright transition-colors"
                      >← Prev</button>
                      <button
                        onClick={() => setPage(p => p + 1)} disabled={!wallet.transactions.next}
                        className="rounded px-3 py-1 text-xs text-dim disabled:opacity-30 hover:text-bright transition-colors"
                      >Next →</button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <p className="text-dim">Wallet not found.</p>
      )}
    </PageWrapper>
  )
}
