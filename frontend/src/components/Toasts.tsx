import { useEffect, useState } from 'react';

export interface Toast {
  id: number;
  message: string;
  kind: 'error' | 'warning' | 'info';
}

// ponytail: module-level pub/sub instead of context — one subscriber, one app.
let nextId = 1;
let toasts: Toast[] = [];
const listeners = new Set<(t: Toast[]) => void>();

function emit() {
  for (const l of listeners) l(toasts);
}

export function showToast(message: string, kind: Toast['kind'] = 'error') {
  const id = nextId++;
  toasts = [...toasts, { id, message, kind }];
  emit();
  setTimeout(() => {
    toasts = toasts.filter((t) => t.id !== id);
    emit();
  }, 5000);
}

export function Toasts() {
  const [list, setList] = useState<Toast[]>(toasts);
  useEffect(() => {
    listeners.add(setList);
    return () => {
      listeners.delete(setList);
    };
  }, []);

  return (
    <div className="toasts">
      {list.map((t) => (
        <div key={t.id} className={`toast toast-${t.kind}`} data-testid="toast">
          {t.message}
        </div>
      ))}
    </div>
  );
}
