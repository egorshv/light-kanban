import { useEffect, useState } from 'react';
import { BoardPage } from './components/BoardPage';
import { BoardsPage } from './components/BoardsPage';
import { Toasts } from './components/Toasts';

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
  const boardMatch = hash.match(/^#\/board\/([^/?]+)/);
  return (
    <>
      {boardMatch ? <BoardPage boardId={boardMatch[1]} /> : <BoardsPage />}
      <Toasts />
    </>
  );
}
