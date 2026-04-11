import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm, Controller } from 'react-hook-form'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/auth/AuthContext'
import { registerUser } from '@/api/auth'
import { AxiosError } from 'axios'
import axios from 'axios'
import AuthLayout from '@/components/layout/AuthLayout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { AlertCircle } from 'lucide-react'

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
    control,
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

  return (
    <AuthLayout>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-bright">Create account</h1>
        <p className="mt-1 text-sm text-faint">Start with simulated funds, risk-free</p>
      </div>

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
            {...register('username', { required: 'Required' })}
            autoComplete="username"
            aria-invalid={!!errors.username}
            className="bg-raised border-edge focus-visible:ring-accent/50"
          />
          {errors.username && <p className="text-xs text-sell">{errors.username.message}</p>}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="email" className="text-dim">Email</Label>
          <Input
            id="email"
            type="email"
            {...register('email', { required: 'Required' })}
            autoComplete="email"
            aria-invalid={!!errors.email}
            className="bg-raised border-edge focus-visible:ring-accent/50"
          />
          {errors.email && <p className="text-xs text-sell">{errors.email.message}</p>}
        </div>

        <div className="space-y-1.5">
          <Label className="text-dim">Home currency</Label>
          <Controller
            control={control}
            name="home_currency"
            rules={{ required: 'Required' }}
            render={({ field }) => (
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger className="bg-raised border-edge focus:ring-accent/50">
                  <SelectValue placeholder="Select currency" />
                </SelectTrigger>
                <SelectContent>
                  {currencies.map((c) => (
                    <SelectItem key={c} value={c}>{c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
          {errors.home_currency && <p className="text-xs text-sell">{errors.home_currency.message}</p>}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="password" className="text-dim">Password</Label>
          <Input
            id="password"
            type="password"
            {...register('password', { required: 'Required', minLength: { value: 8, message: 'Min 8 characters' } })}
            autoComplete="new-password"
            aria-invalid={!!errors.password}
            className="bg-raised border-edge focus-visible:ring-accent/50"
          />
          {errors.password && <p className="text-xs text-sell">{errors.password.message}</p>}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="password2" className="text-dim">Confirm password</Label>
          <Input
            id="password2"
            type="password"
            {...register('password2', {
              required: 'Required',
              validate: (v) => v === watch('password') || 'Passwords do not match',
            })}
            autoComplete="new-password"
            aria-invalid={!!errors.password2}
            className="bg-raised border-edge focus-visible:ring-accent/50"
          />
          {errors.password2 && <p className="text-xs text-sell">{errors.password2.message}</p>}
        </div>

        <Button
          type="submit"
          disabled={isSubmitting}
          className="w-full"
          size="lg"
        >
          {isSubmitting ? 'Creating account…' : 'Create account'}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-faint">
        Already have an account?{' '}
        <Link
          to="/login"
          className="font-medium text-accent hover:text-accent/80 transition-colors"
        >
          Sign in
        </Link>
      </p>
    </AuthLayout>
  )
}
