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
  const { isAuthenticated, setAccessToken } = useAuth()
  const navigate = useNavigate()
  const [serverError, setServerError] = useState('')

  // Fetch available currencies from fx-rates endpoint
  const { data: fxRates } = useQuery({
    queryKey: ['fx-rates-public'],
    queryFn: async () => {
      const { data } = await axios.get('/api/wallets/fx-rates/')
      return data as { to_currency: string }[]
    },
    staleTime: 10 * 60_000,
  })

  // Derive unique currency codes (base + targets)
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
      setAccessToken(result.access)
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

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0f1117] px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-semibold text-white">Create account</h1>
          <p className="mt-1 text-sm text-slate-400">Start with £100,000 in simulated funds</p>
        </div>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-4 rounded-xl border border-slate-800 bg-slate-900 p-6"
        >
          {serverError && (
            <p className="rounded-lg bg-red-900/30 px-3 py-2 text-sm text-red-400">
              {serverError}
            </p>
          )}

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">Username</label>
            <input
              {...register('username', { required: 'Required' })}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              autoComplete="username"
            />
            {errors.username && <p className="mt-1 text-xs text-red-400">{errors.username.message}</p>}
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">Email</label>
            <input
              {...register('email', { required: 'Required' })}
              type="email"
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              autoComplete="email"
            />
            {errors.email && <p className="mt-1 text-xs text-red-400">{errors.email.message}</p>}
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">Home currency</label>
            <select
              {...register('home_currency', { required: 'Required' })}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              {currencies.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">Password</label>
            <input
              {...register('password', { required: 'Required', minLength: { value: 8, message: 'Min 8 characters' } })}
              type="password"
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              autoComplete="new-password"
            />
            {errors.password && <p className="mt-1 text-xs text-red-400">{errors.password.message}</p>}
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">Confirm password</label>
            <input
              {...register('password2', {
                required: 'Required',
                validate: (v) => v === watch('password') || 'Passwords do not match',
              })}
              type="password"
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              autoComplete="new-password"
            />
            {errors.password2 && <p className="mt-1 text-xs text-red-400">{errors.password2.message}</p>}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
          >
            {isSubmitting ? 'Creating account…' : 'Create account'}
          </button>

          <p className="text-center text-xs text-slate-500">
            Already have an account?{' '}
            <Link to="/login" className="text-indigo-400 hover:text-indigo-300">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  )
}
