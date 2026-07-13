import { FormEvent, useState } from 'react';
import { api, ApiError } from '../api/client';
import { ru } from '../i18n/ru';
import { showToast } from './Toasts';

export function LoginPage({ onLogin }: { onLogin: (token: string) => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const register = mode === 'register';

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = register
        ? await api.register({ email, password, name: name.trim() || undefined })
        : await api.login({ email, password });
      onLogin(res.token);
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : ru.loadError, 'error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page">
      <form className="dialog auth-form" onSubmit={submit}>
        <h1 className="dialog-title">{ru.appTitle}</h1>
        <h3>{register ? ru.registerTitle : ru.loginTitle}</h3>
        <input
          autoFocus
          type="email"
          data-testid="auth-email-input"
          placeholder={ru.emailPlaceholder}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          type="password"
          data-testid="auth-password-input"
          placeholder={ru.passwordPlaceholder}
          value={password}
          minLength={8}
          maxLength={128}
          onChange={(e) => setPassword(e.target.value)}
        />
        {register && (
          <input
            data-testid="auth-name-input"
            placeholder={ru.namePlaceholder}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        )}
        <button
          type="submit"
          className="primary"
          data-testid="auth-submit"
          disabled={busy || !email.includes('@') || password.length < 8}
        >
          {register ? ru.registerButton : ru.loginButton}
        </button>
        <a className="auth-google" data-testid="google-login-button" href="/api/v1/auth/google">
          {ru.googleLogin}
        </a>
        <button
          type="button"
          className="link-button"
          data-testid="auth-mode-toggle"
          onClick={() => setMode(register ? 'login' : 'register')}
        >
          {register ? ru.switchToLogin : ru.switchToRegister}
        </button>
      </form>
    </div>
  );
}
