import { useState } from 'react'
import { usePageTitle } from '@/hooks/usePageTitle'
import { Link, useNavigate, Navigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { requestPasswordReset, verifyPasswordResetOTP, confirmPasswordReset } from '@/api/auth'
import { useAuth } from '@/auth/AuthContext'
import { AxiosError } from 'axios'
import { cn } from '@/lib/utils'
import PageWrapper from '@/components/layout/PageWrapper'
import AuthShell from '@/components/layout/AuthShell'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { InputOTP, InputOTPGroup, InputOTPSlot } from '@/components/ui/input-otp'
import { AlertCircle } from 'lucide-react'

interface EmailForm { email: string }
interface PasswordForm { new_password: string; new_password2: string }

const STAGES = ['email', 'otp', 'password'] as const
type Stage = (typeof STAGES)[number]

const STAGE_LABELS: Record<Stage, string> = {
  email: 'Request reset',
  otp: 'Verify code',
  password: 'New password',
}

export default function ForgotPasswordPage() {
  usePageTitle('Reset Password')
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }
  const [stage, setStage] = useState<Stage>('email')
  const [email, setEmail] = useState('')
  const [otp, setOtp] = useState('')
  const [otpValue, setOtpValue] = useState('')
  const [otpError, setOtpError] = useState('')
  const [otpLoading, setOtpLoading] = useState(false)

  const emailForm = useForm<EmailForm>()
  const passwordForm = useForm<PasswordForm>()

  async function onEmailSubmit(data: EmailForm) {
    emailForm.clearErrors()
    try {
      await requestPasswordReset(data.email)
      setEmail(data.email)
      setStage('otp')
    } catch {
      emailForm.setError('root', { message: 'Something went wrong. Please try again.' })
    }
  }

  async function handleOtpVerify() {
    if (otpValue.length < 6) return
    setOtpError('')
    setOtpLoading(true)
    try {
      await verifyPasswordResetOTP(email, otpValue)
      setOtp(otpValue)
      setStage('password')
    } catch (err) {
      const msg =
        err instanceof AxiosError && err.response?.data?.error
          ? err.response.data.error
          : 'Invalid or expired code. Please try again.'
      setOtpError(msg)
    } finally {
      setOtpLoading(false)
    }
  }

  async function onPasswordSubmit(data: PasswordForm) {
    passwordForm.clearErrors()
    try {
      await confirmPasswordReset(email, otp, data.new_password, data.new_password2)
      navigate('/login', { state: { passwordReset: true } })
    } catch (err) {
      const msg =
        err instanceof AxiosError && err.response?.data?.error
          ? err.response.data.error
          : 'Something went wrong. Please try again.'
      passwordForm.setError('root', { message: msg })
    }
  }

  const currentStageIndex = STAGES.indexOf(stage)

  return (
    <PageWrapper>
      <AuthShell>
      {/* Step progress bar */}
      <div className="mb-6 flex gap-1.5">
        {STAGES.map((s, i) => (
          <div
            key={s}
            title={STAGE_LABELS[s]}
            className={cn(
              'h-1 flex-1 rounded-full transition-all duration-300',
              i < currentStageIndex
                ? 'bg-brand/40'
                : i === currentStageIndex
                ? 'bg-brand'
                : 'bg-edge',
            )}
          />
        ))}
      </div>

      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-bright">
          {stage === 'email' && 'Reset password'}
          {stage === 'otp' && 'Check your email'}
          {stage === 'password' && 'Set new password'}
        </h1>
        <p className="mt-1 text-sm text-faint">
          {stage === 'email' && "We'll send a one-time code to your email"}
          {stage === 'otp' && `Enter the 6-digit code sent to ${email}`}
          {stage === 'password' && 'Choose a strong password for your account'}
        </p>
      </div>

      {/* ── Email stage ─────────────────────────────────── */}
      {stage === 'email' && (
        <form onSubmit={emailForm.handleSubmit(onEmailSubmit)} className="space-y-4">
          {emailForm.formState.errors.root && (
            <Alert variant="destructive">
              <AlertCircle className="size-4" />
              <AlertDescription>{emailForm.formState.errors.root.message}</AlertDescription>
            </Alert>
          )}
          <div className="space-y-1.5">
            <Label htmlFor="email" className="text-dim">Email address</Label>
            <Input
              id="email"
              type="email"
              {...emailForm.register('email', {
                required: 'Email is required',
                pattern: { value: /\S+@\S+\.\S+/, message: 'Enter a valid email' },
              })}
              placeholder="you@example.com"
              autoComplete="email"
              aria-invalid={!!emailForm.formState.errors.email}
              className="bg-raised border-edge focus-visible:ring-brand/50"
            />
            {emailForm.formState.errors.email && (
              <p className="text-xs text-sell">{emailForm.formState.errors.email.message}</p>
            )}
          </div>
          <Button
            type="submit"
            disabled={emailForm.formState.isSubmitting}
            className="w-full"
            size="lg"
          >
            {emailForm.formState.isSubmitting ? 'Sending…' : 'Send reset code'}
          </Button>
        </form>
      )}

      {/* ── OTP stage ───────────────────────────────────── */}
      {stage === 'otp' && (
        <div className="space-y-5">
          <div className="flex justify-center">
            <InputOTP
              maxLength={6}
              value={otpValue}
              onChange={(v) => { setOtpValue(v); setOtpError('') }}
            >
              <InputOTPGroup>
                <InputOTPSlot index={0} className="bg-raised border-edge text-bright" />
                <InputOTPSlot index={1} className="bg-raised border-edge text-bright" />
                <InputOTPSlot index={2} className="bg-raised border-edge text-bright" />
                <InputOTPSlot index={3} className="bg-raised border-edge text-bright" />
                <InputOTPSlot index={4} className="bg-raised border-edge text-bright" />
                <InputOTPSlot index={5} className="bg-raised border-edge text-bright" />
              </InputOTPGroup>
            </InputOTP>
          </div>

          {otpError && (
            <Alert variant="destructive">
              <AlertCircle className="size-4" />
              <AlertDescription>{otpError}</AlertDescription>
            </Alert>
          )}

          <Button
            onClick={handleOtpVerify}
            disabled={otpValue.length < 6 || otpLoading}
            className="w-full"
            size="lg"
          >
            {otpLoading ? 'Verifying…' : 'Verify code'}
          </Button>

          <button
            type="button"
            onClick={() => { setStage('email'); setOtpValue(''); setOtpError('') }}
            className="w-full text-center text-[11px] text-faint hover:text-dim transition-colors"
          >
            Use a different email
          </button>
        </div>
      )}

      {/* ── New password stage ──────────────────────────── */}
      {stage === 'password' && (
        <form onSubmit={passwordForm.handleSubmit(onPasswordSubmit)} className="space-y-4">
          {passwordForm.formState.errors.root && (
            <Alert variant="destructive">
              <AlertCircle className="size-4" />
              <AlertDescription>{passwordForm.formState.errors.root.message}</AlertDescription>
            </Alert>
          )}
          <div className="space-y-1.5">
            <Label htmlFor="new_password" className="text-dim">New password</Label>
            <Input
              id="new_password"
              type="password"
              {...passwordForm.register('new_password', {
                required: 'Password is required',
                minLength: { value: 8, message: 'Minimum 8 characters' },
              })}
              placeholder="••••••••"
              autoComplete="new-password"
              aria-invalid={!!passwordForm.formState.errors.new_password}
              className="bg-raised border-edge focus-visible:ring-brand/50"
            />
            {passwordForm.formState.errors.new_password && (
              <p className="text-xs text-sell">{passwordForm.formState.errors.new_password.message}</p>
            )}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="new_password2" className="text-dim">Confirm password</Label>
            <Input
              id="new_password2"
              type="password"
              {...passwordForm.register('new_password2', {
                required: 'Please confirm your password',
                validate: (v) => v === passwordForm.watch('new_password') || 'Passwords do not match',
              })}
              placeholder="••••••••"
              autoComplete="new-password"
              aria-invalid={!!passwordForm.formState.errors.new_password2}
              className="bg-raised border-edge focus-visible:ring-brand/50"
            />
            {passwordForm.formState.errors.new_password2 && (
              <p className="text-xs text-sell">{passwordForm.formState.errors.new_password2.message}</p>
            )}
          </div>
          <Button
            type="submit"
            disabled={passwordForm.formState.isSubmitting}
            className="w-full"
            size="lg"
          >
            {passwordForm.formState.isSubmitting ? 'Saving…' : 'Reset password'}
          </Button>
        </form>
      )}

      <p className="mt-6 text-center text-[11px] text-faint">
        <Link to="/login" className="hover:text-dim transition-colors">← Back to sign in</Link>
      </p>
      </AuthShell>
    </PageWrapper>
  )
}
