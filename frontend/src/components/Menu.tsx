import { ReactNode, useEffect, useRef, useState } from 'react';

interface Props {
  buttonTestId: string;
  buttonLabel?: string;
  children: (close: () => void) => ReactNode;
}

/** Кнопка «⋯» с выпадающим меню; закрывается по клику вне и Esc. */
export function Menu({ buttonTestId, buttonLabel = '⋯', children }: Props) {
  const [open, setOpen] = useState(false);
  // ponytail: fixed-позиционирование по клику, чтобы dropdown не резался overflow-скроллом
  // колонок; при скролле с открытым меню оно не следует за кнопкой (закрывается кликом/Esc).
  const [pos, setPos] = useState({ top: 0, right: 0 });
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onDown);
    window.addEventListener('keydown', onKey, true);
    return () => {
      document.removeEventListener('mousedown', onDown);
      window.removeEventListener('keydown', onKey, true);
    };
  }, [open]);

  return (
    <div className="menu" ref={ref}>
      <button
        className="menu-button"
        data-testid={buttonTestId}
        onClick={(e) => {
          e.stopPropagation();
          const r = e.currentTarget.getBoundingClientRect();
          setPos({ top: r.bottom + 2, right: window.innerWidth - r.right });
          setOpen((o) => !o);
        }}
      >
        {buttonLabel}
      </button>
      {open && (
        <div
          className="menu-dropdown"
          style={{ position: 'fixed', top: pos.top, right: pos.right }}
          onClick={(e) => e.stopPropagation()}
        >
          {children(() => setOpen(false))}
        </div>
      )}
    </div>
  );
}
