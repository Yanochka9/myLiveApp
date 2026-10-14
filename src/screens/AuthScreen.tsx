import { useState, type FormEvent } from 'react'
import { authApi } from '../data/firebase'
import { Spinner } from '../components/Spinner'

type Mode = 'signin' | 'signup'

const ERRORS: Record<string, string> = {
  'auth/invalid-credential': 'Неверная почта или пароль',
  'auth/invalid-email': 'Некорректный адрес почты',
  'auth/user-not-found': 'Пользователь не найден',
  'auth/wrong-password': 'Неверный пароль',
  'auth/email-already-in-use': 'Эта почта уже зарегистрирована',
  'auth/weak-password': 'Пароль должен быть не короче 6 символов',
  'auth/too-many-requests': 'Слишком много попыток, попробуйте позже',
  'auth/network-request-failed': 'Нет соединения с интернетом',
}

const message = (e: unknown) => ERRORS[(e as { code?: string }).code ?? ''] ?? 'Что-то пошло не так'

export function AuthScreen() {
  const [mode, setMode] = useState<Mode>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (mode === 'signin') await authApi.signIn(email.trim(), password)
      else await authApi.signUp(email.trim(), password)
    } catch (err) {
      setError(message(err))
      setBusy(false)
    }
  }

  const reset = async () => {
    if (!email.trim()) return setError('Введите почту, чтобы сбросить пароль')
    try {
      await authApi.resetPassword(email.trim())
      setError('')
      setInfo('Письмо для сброса пароля отправлено')
    } catch (err) {
      setError(message(err))
    }
  }

  return (
    <div className="auth fade-in">
      <img className="auth-logo" src="/icons/icon-192.png" alt="" />
      <h1>День</h1>
      <p>Работа и личная жизнь — в одном спокойном месте</p>

      <form onSubmit={submit}>
        <div className="form-group card">
          <input
            className="field"
            type="email"
            inputMode="email"
            autoComplete="email"
            placeholder="Почта"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            className="field"
            type="password"
            autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
            placeholder="Пароль"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={6}
            required
          />
        </div>
        <div className="auth-error" role="alert" style={info && !error ? { color: 'var(--success)' } : undefined}>
          {error || info}
        </div>
        <button type="submit" className="primary-btn" disabled={busy}>
          {busy && <Spinner />}
          {mode === 'signin' ? 'Войти' : 'Создать аккаунт'}
        </button>
      </form>

      <div className="auth-links">
        <button type="button" className="text-btn" onClick={() => (setMode(mode === 'signin' ? 'signup' : 'signin'), setError(''))}>
          {mode === 'signin' ? 'Регистрация' : 'У меня есть аккаунт'}
        </button>
        {mode === 'signin' && (
          <button type="button" className="text-btn" onClick={reset}>
            Забыли пароль?
          </button>
        )}
      </div>
    </div>
  )
}
