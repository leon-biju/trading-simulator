import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/auth/AuthContext'
import { registerUser } from '@/api/auth'
import { AxiosError } from 'axios'
import axios from 'axios'

interface RegisterForm {
  username: string
  email: string
  password: string
  password2: string
  home_currency: string
}

export default function RegisterPage() {
  const { isAuthenticated, loginWithToken } = useAuth()
  const navigate = useNavigate()
  const [serverError, setServerError] = useState('')

  const { data: fxRates } = useQuery({
    queryKey: ['fx-rates-public'],
    queryFn: async () => {
      const { data } = await axios.get('/api/wallets/fx-rates/')
      return data as { to_currency: string }[]
    },
    staleTime: 10 * 60_000,
  })

  const currencies = fxRates
    ? Array.from(new Set(fxRates.map((r) => r.to_currency))).sort()
    : ['GBP', 'USD', 'EUR']

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RegisterForm>({ defaultValues: { home_currency: 'GBP' } })

  if (isAuthenticated) {
    navigate('/dashboard', { replace: true })
    return null
  }

  async function onSubmit(data: RegisterForm) {
    setServerError('')
    try {
      const result = await registerUser(data)
      loginWithToken(result.access, result.user)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      if (err instanceof AxiosError && err.response?.data) {
        const d = err.response.data
        setServerError(d.error ?? JSON.stringify(d))
      } else {
        setServerError('Registration failed. Please try again.')
      }
    }
  }

  const inputCls = 'w-full rounded border border-edge bg-raised px-3 py-2 text-sm text-bright placeholder-faint focus:border-accent focus:outline-none transition-colors'

  return (
    <div className="flex min-h-screen items-center justify-center bg-base px-4 py-8">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-lg font-bold text-base">T</div>
          <h1 className="text-xl font-semibold text-bright">Create account</h1>
          <p className="mt-1 text-sm text-faint">Start with £100,000 in simulated funds</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 rounded-lg border border-edge bg-panel p-6">
          {serverError && (
            <p className="rounded border border-sell/20 bg-sell/8 px-3 py-2 text-sm text-sell">
              {serverError}
            </p>
          )}

          <div>
            <label className="mb-1.5 block text-[11px] uppercase tracking-wider text-faint">Username</label>
            <input {...register('username', { required: 'Required' })} className={inputCls} autoComplete="username" />
            {errors.username && <p className="mt-1 text-xs text-sell">{errors.username.message}</p>}
          </div>

          <div>
            <label className="mb-1.5 block text-[11px] uppercase tracking-wider text-faint">Email</label>
            <input {...register('email', { required: 'Required' })} type="email" className={inputCls} autoComplete="email" />
            {errors.email && <p className="mt-1 text-xs text-sell">{errors.email.message}</p>}
          </div>

          <div>
            <label className="mb-1.5 block text-[11px] uppercase tracking-wider text-faint">Home currency</label>
            <select {...register('home_currency', { required: 'Required' })} className={inputCls}>
              {currencies.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-[11px] uppercase tracking-wider text-faint">Password</label>
            <input
              {...register('password', { required: 'Required', minLength: { value: 8, message: 'Min 8 characters' } })}
              type="password" className={inputCls} autoComplete="new-password"
            />
            {errors.password && <p className="mt-1 text-xs text-sell">{errors.password.message}</p>}
          </div>

          <div>
            <label className="mb-1.5 block text-[11px] uppercase tracking-wider text-faint">Confirm password</label>
            <input
              {...register('password2', {
                required: 'Required',
                validate: (v) => v === watch('password') || 'Passwords do not match',
              })}
              type="password" className={inputCls} autoComplete="new-password"
            />
            {errors.password2 && <p className="mt-1 text-xs text-sell">{errors.password2.message}</p>}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded bg-accent px-4 py-2.5 text-sm font-medium text-base transition hover:bg-accent/90 disabled:opacity-50"
          >
            {isSubmitting ? 'Creating account…' : 'Create account'}
          </button>

          <p className="text-center text-[11px] text-faint">
            Already have an account?{' '}
            <Link to="/login" className="text-accent hover:text-accent/80 transition-colors">Sign in</Link>
          </p>
        </form>
      </div>
    </div>
  )
}
