import { useEffect, useState } from 'react';
import { BoardPage } from './components/BoardPage';
import { BoardsPage } from './components/BoardsPage';
import { LoginPage } from './components/LoginPage';
import { Toasts } from './components/Toasts';

// Возврат из Google OAuth: токен приходит во фрагменте (#/auth?token=…),
// подхватываем до первого рендера и чистим URL.
const oauth = window.location.hash.match(/^#\/auth\?token=([^&]+)/);
if (oauth) {
  localStorage.setItem('kanban_token', oauth[1]);
  history.replaceState(null, '', '/#/');
}

// Крошечный hash-роутер: '#/' — список досок, '#/board/{id}' — доска.
function useHashRoute(): string {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const onChange = () => setHash(window.location.hash);
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return hash;
}

export function App() {
  const hash = useHashRoute();
  const [token, setToken] = useState(() => localStorage.getItem('kanban_token'));

  if (!token) {
    return (
      <>
        <LoginPage
          onLogin={(t) => {
            localStorage.setItem('kanban_token', t);
            setToken(t);
          }}
        />
        <Toasts />
      </>
    );
  }

  const boardMatch = hash.match(/^#\/board\/([^/?]+)/);
  return (
    <>
      {boardMatch ? <BoardPage boardId={boardMatch[1]} /> : <BoardsPage />}
      <Toasts />
    </>
  );
}
