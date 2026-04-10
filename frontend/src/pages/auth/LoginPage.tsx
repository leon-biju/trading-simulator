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

  const inputCls = 'w-full rounded border border-edge bg-raised px-3 py-2 text-sm text-bright placeholder-faint focus:border-accent focus:outline-none transition-colors'

  return (
    <div className="flex min-h-screen items-center justify-center bg-base px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-lg font-bold text-base">T</div>
          <h1 className="text-xl font-semibold text-bright">TradeSim</h1>
          <p className="mt-1 text-sm text-faint">Sign in to your account</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 rounded-lg border border-edge bg-panel p-6">
          {serverError && (
            <p className="rounded border border-sell/20 bg-sell/8 px-3 py-2 text-sm text-sell">
              {serverError}
            </p>
          )}

          <div>
            <label className="mb-1.5 block text-[11px] uppercase tracking-wider text-faint">Username</label>
            <input
              {...register('username', { required: 'Username is required' })}
              className={inputCls}
              placeholder="your_username"
              autoComplete="username"
            />
            {errors.username && <p className="mt-1 text-xs text-sell">{errors.username.message}</p>}
          </div>

          <div>
            <label className="mb-1.5 block text-[11px] uppercase tracking-wider text-faint">Password</label>
            <input
              {...register('password', { required: 'Password is required' })}
              type="password"
              className={inputCls}
              placeholder="••••••••"
              autoComplete="current-password"
            />
            {errors.password && <p className="mt-1 text-xs text-sell">{errors.password.message}</p>}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded bg-accent px-4 py-2.5 text-sm font-medium text-base transition hover:bg-accent/90 disabled:opacity-50"
          >
            {isSubmitting ? 'Signing in…' : 'Sign in'}
          </button>

          <div className="flex items-center justify-between text-[11px] text-faint">
            <Link to="/register" className="hover:text-dim transition-colors">Create account</Link>
            <a href="/accounts/password_reset/" className="hover:text-dim transition-colors">Forgot password?</a>
          </div>
        </form>
      </div>
    </div>
  )
}
