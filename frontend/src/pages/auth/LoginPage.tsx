import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { useAuth } from '@/auth/AuthContext'
import { AxiosError } from 'axios'

interface LoginForm {
  username: string
  password: string
}

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [serverError, setServerError] = useState('')

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>()

  // Already logged in
  if (isAuthenticated) {
    navigate('/dashboard', { replace: true })
    return null
  }

  async function onSubmit(data: LoginForm) {
    setServerError('')
    try {
      await login(data)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      if (err instanceof AxiosError && err.response?.status === 401) {
        setServerError('Invalid username or password.')
      } else {
        setServerError('Something went wrong. Please try again.')
      }
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0f1117] px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-semibold text-white">Trading Simulator</h1>
          <p className="mt-1 text-sm text-slate-400">Sign in to your account</p>
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
            <label className="mb-1.5 block text-sm font-medium text-slate-300">
              Username
            </label>
            <input
              {...register('username', { required: 'Username is required' })}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              placeholder="your_username"
              autoComplete="username"
            />
            {errors.username && (
              <p className="mt-1 text-xs text-red-400">{errors.username.message}</p>
            )}
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-300">
              Password
            </label>
            <input
              {...register('password', { required: 'Password is required' })}
              type="password"
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              placeholder="••••••••"
              autoComplete="current-password"
            />
            {errors.password && (
              <p className="mt-1 text-xs text-red-400">{errors.password.message}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
          >
            {isSubmitting ? 'Signing in…' : 'Sign in'}
          </button>

          <div className="flex items-center justify-between text-xs text-slate-500">
            <Link to="/register" className="hover:text-slate-300">
              Create account
            </Link>
            <a href="/accounts/password_reset/" className="hover:text-slate-300">
              Forgot password?
            </a>
          </div>
        </form>
      </div>
    </div>
  )
}
