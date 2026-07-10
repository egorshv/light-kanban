import { ReactNode, useEffect } from 'react';
import { ru } from '../i18n/ru';

interface Props {
  title: string;
  message?: string;
  children?: ReactNode; // дополнительные контролы (например, выбор колонки-приёмника)
  acceptLabel?: string;
  acceptDisabled?: boolean;
  onAccept: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  title,
  message,
  children,
  acceptLabel,
  acceptDisabled,
  onAccept,
  onCancel,
}: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onCancel();
      }
    };
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [onCancel]);

  return (
    <div className="dialog-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onCancel()}>
      <div className="dialog" data-testid="confirm-dialog" role="dialog" aria-label={title}>
        <h3 className="dialog-title">{title}</h3>
        {message && <p className="dialog-message">{message}</p>}
        {children}
        <div className="dialog-actions">
          <button data-testid="confirm-cancel" onClick={onCancel}>
            {ru.cancel}
          </button>
          <button
            className="danger"
            data-testid="confirm-accept"
            disabled={acceptDisabled}
            onClick={onAccept}
          >
            {acceptLabel ?? ru.confirm}
          </button>
        </div>
      </div>
    </div>
  );
}
