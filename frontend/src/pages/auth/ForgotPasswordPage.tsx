import { useRef, useState, ClipboardEvent, KeyboardEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { requestPasswordReset, verifyPasswordResetOTP, confirmPasswordReset } from '@/api/auth'
import { AxiosError } from 'axios'

interface EmailForm { email: string }
interface PasswordForm { new_password: string; new_password2: string }

const inputCls = 'w-full rounded border border-edge bg-raised px-3 py-2 text-sm text-bright placeholder-faint focus:border-accent focus:outline-none transition-colors'

function OtpInput({ onComplete }: { onComplete: (otp: string) => void }) {
  const [digits, setDigits] = useState(['', '', '', '', '', ''])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const refs = useRef<(HTMLInputElement | null)[]>([])

  function update(index: number, value: string) {
    const d = [...digits]
    d[index] = value
    setDigits(d)
    if (value && index < 5) refs.current[index + 1]?.focus()
  }

  function onKeyDown(index: number, e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      refs.current[index - 1]?.focus()
    }
  }

  function onPaste(e: ClipboardEvent<HTMLInputElement>) {
    e.preventDefault()
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
    if (!pasted) return
    const d = [...digits]
    for (let i = 0; i < pasted.length; i++) d[i] = pasted[i]
    setDigits(d)
    refs.current[Math.min(pasted.length, 5)]?.focus()
  }

  async function verify() {
    const otp = digits.join('')
    if (otp.length < 6) { setError('Enter all 6 digits.'); return }
    setError('')
    setLoading(true)
    try {
      await onComplete(otp)
    } catch (err) {
      const msg =
        err instanceof AxiosError && err.response?.data?.error
          ? err.response.data.error
          : 'Something went wrong. Please try again.'
      setError(msg)
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-2 justify-center">
        {digits.map((d, i) => (
          <input
            key={i}
            ref={el => { refs.current[i] = el }}
            type="text"
            inputMode="numeric"
            maxLength={1}
            value={d}
            onChange={e => update(i, e.target.value.replace(/\D/g, '').slice(-1))}
            onKeyDown={e => onKeyDown(i, e)}
            onPaste={onPaste}
            className="w-10 h-12 rounded border border-edge bg-raised text-center text-lg font-mono text-bright focus:border-accent focus:outline-none transition-colors"
          />
        ))}
      </div>
      {error && (
        <p className="rounded border border-sell/20 bg-sell/8 px-3 py-2 text-sm text-sell text-center">
          {error}
        </p>
      )}
      <button
        type="button"
        onClick={verify}
        disabled={loading || digits.join('').length < 6}
        className="w-full rounded bg-accent px-4 py-2.5 text-sm font-medium text-base transition hover:bg-accent/90 disabled:opacity-50"
      >
        {loading ? 'Verifying…' : 'Verify code'}
      </button>
    </div>
  )
}

export default function ForgotPasswordPage() {
  const navigate = useNavigate()
  const [stage, setStage] = useState<'email' | 'otp' | 'password'>('email')
  const [email, setEmail] = useState('')
  const [otp, setOtp] = useState('')

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

  async function onOtpComplete(code: string) {
    await verifyPasswordResetOTP(email, code)
    setOtp(code)
    setStage('password')
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

  return (
    <div className="flex min-h-screen items-center justify-center bg-base px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-lg font-bold text-base">T</div>
          <h1 className="text-xl font-semibold text-bright">TradeSim</h1>
          <p className="mt-1 text-sm text-faint">
            {stage === 'email' && 'Reset your password'}
            {stage === 'otp' && 'Enter your reset code'}
            {stage === 'password' && 'Set a new password'}
          </p>
        </div>

        <div className="rounded-lg border border-edge bg-panel p-6 space-y-4">
          {stage === 'email' && (
            <form onSubmit={emailForm.handleSubmit(onEmailSubmit)} className="space-y-4">
              {emailForm.formState.errors.root && (
                <p className="rounded border border-sell/20 bg-sell/8 px-3 py-2 text-sm text-sell">
                  {emailForm.formState.errors.root.message}
                </p>
              )}
              <div>
                <label className="mb-1.5 block text-[11px] uppercase tracking-wider text-faint">Email address</label>
                <input
                  {...emailForm.register('email', {
                    required: 'Email is required',
                    pattern: { value: /\S+@\S+\.\S+/, message: 'Enter a valid email' },
                  })}
                  type="email"
                  className={inputCls}
                  placeholder="you@example.com"
                  autoComplete="email"
                />
                {emailForm.formState.errors.email && (
                  <p className="mt-1 text-xs text-sell">{emailForm.formState.errors.email.message}</p>
                )}
              </div>
              <button
                type="submit"
                disabled={emailForm.formState.isSubmitting}
                className="w-full rounded bg-accent px-4 py-2.5 text-sm font-medium text-base transition hover:bg-accent/90 disabled:opacity-50"
              >
                {emailForm.formState.isSubmitting ? 'Sending…' : 'Send reset code'}
              </button>
            </form>
          )}

          {stage === 'otp' && (
            <>
              <p className="text-sm text-dim text-center">
                If an account exists for <span className="text-bright">{email}</span>, we've sent a 6-digit code. It expires in 10 minutes.
              </p>
              <OtpInput onComplete={onOtpComplete} />
              <button
                type="button"
                onClick={() => setStage('email')}
                className="w-full text-center text-[11px] text-faint hover:text-dim transition-colors"
              >
                Use a different email
              </button>
            </>
          )}

          {stage === 'password' && (
            <form onSubmit={passwordForm.handleSubmit(onPasswordSubmit)} className="space-y-4">
              {passwordForm.formState.errors.root && (
                <p className="rounded border border-sell/20 bg-sell/8 px-3 py-2 text-sm text-sell">
                  {passwordForm.formState.errors.root.message}
                </p>
              )}
              <div>
                <label className="mb-1.5 block text-[11px] uppercase tracking-wider text-faint">New password</label>
                <input
                  {...passwordForm.register('new_password', {
                    required: 'Password is required',
                    minLength: { value: 8, message: 'Minimum 8 characters' },
                  })}
                  type="password"
                  className={inputCls}
                  placeholder="••••••••"
                  autoComplete="new-password"
                />
                {passwordForm.formState.errors.new_password && (
                  <p className="mt-1 text-xs text-sell">{passwordForm.formState.errors.new_password.message}</p>
                )}
              </div>
              <div>
                <label className="mb-1.5 block text-[11px] uppercase tracking-wider text-faint">Confirm password</label>
                <input
                  {...passwordForm.register('new_password2', {
                    required: 'Please confirm your password',
                    validate: v => v === passwordForm.watch('new_password') || 'Passwords do not match',
                  })}
                  type="password"
                  className={inputCls}
                  placeholder="••••••••"
                  autoComplete="new-password"
                />
                {passwordForm.formState.errors.new_password2 && (
                  <p className="mt-1 text-xs text-sell">{passwordForm.formState.errors.new_password2.message}</p>
                )}
              </div>
              <button
                type="submit"
                disabled={passwordForm.formState.isSubmitting}
                className="w-full rounded bg-accent px-4 py-2.5 text-sm font-medium text-base transition hover:bg-accent/90 disabled:opacity-50"
              >
                {passwordForm.formState.isSubmitting ? 'Saving…' : 'Reset password'}
              </button>
            </form>
          )}

          <div className="text-center text-[11px] text-faint">
            <Link to="/login" className="hover:text-dim transition-colors">Back to sign in</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
