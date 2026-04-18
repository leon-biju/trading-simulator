import { useState } from 'react'
import { usePageTitle } from '@/hooks/usePageTitle'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { AxiosError } from 'axios'
import PageWrapper from '@/components/layout/PageWrapper'
import { useAuth } from '@/auth/AuthContext'
import { updateProfile, changePassword } from '@/api/profile'
import api from '@/lib/axios'

interface AccountForm {
  display_name: string
}

interface PreferencesForm {
  home_currency: string
}

interface PasswordForm {
  current_password: string
  new_password: string
  new_password2: string
}

const inputCls =
  'w-full rounded border border-edge bg-raised px-3 py-2 text-sm text-bright placeholder-faint focus:border-brand focus:outline-none transition-colors'
const readOnlyCls =
  'w-full rounded border border-edge bg-base px-3 py-2 text-sm text-dim cursor-not-allowed select-none'

function SectionHeader({ children }: { children: string }) {
  return (
    <h2 className="mb-4 border-b border-edge pb-3 text-[11px] uppercase tracking-wider text-faint">
      {children}
    </h2>
  )
}

function FieldLabel({ children }: { children: string }) {
  return (
    <label className="mb-1 block text-[11px] uppercase tracking-wider text-faint">{children}</label>
  )
}

function SaveRow({
  isPending,
  isSuccess,
  label = 'Save',
}: {
  isPending: boolean
  isSuccess: boolean
  label?: string
}) {
  return (
    <div className="flex items-center gap-3 pt-1">
      <button
        type="submit"
        disabled={isPending}
        className="rounded bg-brand px-4 py-2 text-sm font-medium text-base transition hover:bg-brand/90 disabled:opacity-50"
      >
        {isPending ? 'Saving…' : label}
      </button>
      {isSuccess && <span className="text-xs text-buy">Saved</span>}
    </div>
  )
}

export default function SettingsPage() {
  usePageTitle('Settings')
  const { user, refreshUser } = useAuth()

  // ── Account ──────────────────────────────────────────────────────────────
  const [accountError, setAccountError] = useState<string | null>(null)
  const {
    register: regAccount,
    handleSubmit: submitAccount,
    formState: { errors: errAccount },
  } = useForm<AccountForm>({
    defaultValues: { display_name: user?.display_name ?? '' },
  })
  const accountMutation = useMutation({
    mutationFn: (data: AccountForm) => updateProfile(data),
    onSuccess: () => {
      setAccountError(null)
      refreshUser()
    },
    onError: (err: AxiosError<{ error?: string }>) => {
      setAccountError(err.response?.data?.error ?? 'Failed to update.')
    },
  })

  // ── Preferences ──────────────────────────────────────────────────────────
  const [prefsError, setPrefsError] = useState<string | null>(null)
  const { data: fxRates } = useQuery({
    queryKey: ['fx-rates-public'],
    queryFn: async () => {
      const { data } = await api.get('/api/wallets/fx-rates/')
      return data as { to_currency: string }[]
    },
    staleTime: 10 * 60_000,
  })
  const currencies = fxRates
    ? Array.from(new Set(fxRates.map((r) => r.to_currency))).sort()
    : ['EUR', 'GBP', 'USD']

  const {
    register: regPrefs,
    handleSubmit: submitPrefs,
    formState: { errors: errPrefs },
  } = useForm<PreferencesForm>({
    defaultValues: { home_currency: user?.home_currency ?? 'USD' },
  })
  const prefsMutation = useMutation({
    mutationFn: (data: PreferencesForm) => updateProfile(data),
    onSuccess: () => {
      setPrefsError(null)
      refreshUser()
    },
    onError: (err: AxiosError<{ error?: string }>) => {
      setPrefsError(err.response?.data?.error ?? 'Failed to update.')
    },
  })

  // ── Security ─────────────────────────────────────────────────────────────
  const [pwError, setPwError] = useState<string | null>(null)
  const {
    register: regPw,
    handleSubmit: submitPw,
    watch: watchPw,
    reset: resetPw,
    formState: { errors: errPw },
  } = useForm<PasswordForm>()
  const newPw = watchPw('new_password')
  const pwMutation = useMutation({
    mutationFn: changePassword,
    onSuccess: () => {
      setPwError(null)
      resetPw()
    },
    onError: (err: AxiosError<{ error?: string }>) => {
      setPwError(err.response?.data?.error ?? 'Failed to change password.')
    },
  })

  return (
    <PageWrapper>
      <div className="max-w-xl space-y-6">
        <h1 className="text-lg font-semibold text-bright">Settings</h1>

        {/* Account */}
        <section className="rounded-lg border border-edge bg-panel p-5">
          <SectionHeader>Account</SectionHeader>
          <form
            onSubmit={submitAccount((data) => accountMutation.mutate(data))}
            className="space-y-4"
          >
            <div>
              <FieldLabel>Display name</FieldLabel>
              <input
                {...regAccount('display_name', {
                  maxLength: { value: 100, message: 'Max 100 characters' },
                })}
                placeholder="Your name"
                className={inputCls}
              />
              {errAccount.display_name && (
                <p className="mt-1 text-xs text-sell">{errAccount.display_name.message}</p>
              )}
            </div>
            <div>
              <FieldLabel>Username</FieldLabel>
              <input value={user?.username ?? ''} readOnly className={readOnlyCls} />
            </div>
            <div>
              <FieldLabel>Email</FieldLabel>
              <input value={user?.email ?? ''} readOnly className={readOnlyCls} />
            </div>
            {accountError && <p className="text-xs text-sell">{accountError}</p>}
            <SaveRow
              isPending={accountMutation.isPending}
              isSuccess={accountMutation.isSuccess}
            />
          </form>
        </section>

        {/* Preferences */}
        <section className="rounded-lg border border-edge bg-panel p-5">
          <SectionHeader>Preferences</SectionHeader>
          <form
            onSubmit={submitPrefs((data) => prefsMutation.mutate(data))}
            className="space-y-4"
          >
            <div>
              <FieldLabel>Home currency</FieldLabel>
              <select
                {...regPrefs('home_currency', { required: 'Required' })}
                className={inputCls}
              >
                {currencies.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
              {errPrefs.home_currency && (
                <p className="mt-1 text-xs text-sell">{errPrefs.home_currency.message}</p>
              )}
            </div>
            {prefsError && <p className="text-xs text-sell">{prefsError}</p>}
            <SaveRow
              isPending={prefsMutation.isPending}
              isSuccess={prefsMutation.isSuccess}
            />
          </form>
        </section>

        {/* Security */}
        <section className="rounded-lg border border-edge bg-panel p-5">
          <SectionHeader>Security</SectionHeader>
          <form
            onSubmit={submitPw((data) => pwMutation.mutate(data))}
            className="space-y-4"
          >
            <div>
              <FieldLabel>Current password</FieldLabel>
              <input
                type="password"
                autoComplete="current-password"
                {...regPw('current_password', { required: 'Required' })}
                className={inputCls}
              />
              {errPw.current_password && (
                <p className="mt-1 text-xs text-sell">{errPw.current_password.message}</p>
              )}
            </div>
            <div>
              <FieldLabel>New password</FieldLabel>
              <input
                type="password"
                autoComplete="new-password"
                {...regPw('new_password', {
                  required: 'Required',
                  minLength: { value: 8, message: 'Minimum 8 characters' },
                })}
                className={inputCls}
              />
              {errPw.new_password && (
                <p className="mt-1 text-xs text-sell">{errPw.new_password.message}</p>
              )}
            </div>
            <div>
              <FieldLabel>Confirm new password</FieldLabel>
              <input
                type="password"
                autoComplete="new-password"
                {...regPw('new_password2', {
                  required: 'Required',
                  validate: (v) => v === newPw || 'Passwords do not match',
                })}
                className={inputCls}
              />
              {errPw.new_password2 && (
                <p className="mt-1 text-xs text-sell">{errPw.new_password2.message}</p>
              )}
            </div>
            {pwError && <p className="text-xs text-sell">{pwError}</p>}
            <SaveRow
              isPending={pwMutation.isPending}
              isSuccess={pwMutation.isSuccess}
              label="Change password"
            />
          </form>
        </section>
      </div>
    </PageWrapper>
  )
}
