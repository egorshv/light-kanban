import { ReactNode, useEffect, useRef, useState } from 'react';

interface Props {
  buttonTestId: string;
  buttonLabel?: string;
  children: (close: () => void) => ReactNode;
}

/** Кнопка «⋯» с выпадающим меню; закрывается по клику вне и Esc. */
export function Menu({ buttonTestId, buttonLabel = '⋯', children }: Props) {
  const [open, setOpen] = useState(false);
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
          setOpen((o) => !o);
        }}
      >
        {buttonLabel}
      </button>
      {open && (
        <div className="menu-dropdown" onClick={(e) => e.stopPropagation()}>
          {children(() => setOpen(false))}
        </div>
      )}
    </div>
  );
}
