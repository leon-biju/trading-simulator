import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { useAuth } from '@/auth/AuthContext'
import { AxiosError } from 'axios'
import AuthLayout from '@/components/layout/AuthLayout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle, CheckCircle } from 'lucide-react'

interface LoginForm {
  username: string
  password: string
}

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [serverError, setServerError] = useState('')
  const passwordReset = (location.state as { passwordReset?: boolean } | null)?.passwordReset

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

  return (
    <AuthLayout>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-bright">Welcome back</h1>
        <p className="mt-1 text-sm text-faint">Sign in to your account</p>
      </div>

      {passwordReset && (
        <Alert className="mb-4 border-buy/20 bg-buy/8 text-buy">
          <CheckCircle className="size-4 !text-buy" />
          <AlertDescription className="text-buy">
            Password updated. Sign in with your new password.
          </AlertDescription>
        </Alert>
      )}
      {serverError && (
        <Alert variant="destructive" className="mb-4">
          <AlertCircle className="size-4" />
          <AlertDescription>{serverError}</AlertDescription>
        </Alert>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="username" className="text-dim">Username</Label>
          <Input
            id="username"
            {...register('username', { required: 'Username is required' })}
            placeholder="your_username"
            autoComplete="username"
            aria-invalid={!!errors.username}
            className="bg-raised border-edge focus-visible:ring-accent/50"
          />
          {errors.username && (
            <p className="text-xs text-sell">{errors.username.message}</p>
          )}
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <Label htmlFor="password" className="text-dim">Password</Label>
            <Link
              to="/forgot-password"
              className="text-[11px] text-faint hover:text-dim transition-colors"
            >
              Forgot password?
            </Link>
          </div>
          <Input
            id="password"
            type="password"
            {...register('password', { required: 'Password is required' })}
            placeholder="••••••••"
            autoComplete="current-password"
            aria-invalid={!!errors.password}
            className="bg-raised border-edge focus-visible:ring-accent/50"
          />
          {errors.password && (
            <p className="text-xs text-sell">{errors.password.message}</p>
          )}
        </div>

        <Button
          type="submit"
          disabled={isSubmitting}
          className="w-full"
          size="lg"
        >
          {isSubmitting ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-faint">
        Don't have an account?{' '}
        <Link
          to="/register"
          className="font-medium text-accent hover:text-accent/80 transition-colors"
        >
          Create one
        </Link>
      </p>
    </AuthLayout>
  )
}
