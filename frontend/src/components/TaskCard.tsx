import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import type { Column, TaskInBoard } from '../api/types';
import { ru } from '../i18n/ru';
import { Menu } from './Menu';

export function isOverdue(task: { due_date: string | null; completed_at: string | null }): boolean {
  if (!task.due_date || task.completed_at) return false;
  const today = new Date();
  const iso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  return task.due_date < iso;
}

function formatDue(dueDate: string): string {
  const [, m, d] = dueDate.split('-');
  return `${d}.${m}`;
}

interface Props {
  task: TaskInBoard;
  columns: Column[];
  onOpen: (taskId: string) => void;
  onMoveTo: (taskId: string, columnId: string) => void;
  onDelete: (taskId: string) => void;
}

export function TaskCard({ task, columns, onOpen, onMoveTo, onDelete }: Props) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: task.id,
    data: { type: 'task', columnId: task.column_id },
  });

  const overdue = isOverdue(task);
  const classes = [
    'task-card',
    `prio-${task.priority}`,
    task.completed_at ? 'completed' : '',
    isDragging ? 'dragging' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div
      ref={setNodeRef}
      className={classes}
      data-testid="task-card"
      data-task-id={task.id}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      onClick={() => onOpen(task.id)}
      {...attributes}
      {...listeners}
    >
      <div className="task-card-row">
        <span className="task-card-title">
          {task.completed_at && <span className="task-check">✓ </span>}
          {task.title}
        </span>
        <Menu buttonTestId="task-menu-button">
          {(close) => (
            <>
              <div className="menu-section-label">{ru.moveTo}</div>
              {columns
                .filter((c) => c.id !== task.column_id)
                .map((c) => (
                  <button
                    key={c.id}
                    data-testid="task-move-option"
                    onClick={() => {
                      close();
                      onMoveTo(task.id, c.id);
                    }}
                  >
                    {c.name}
                  </button>
                ))}
              <button
                className="danger"
                data-testid="task-delete-option"
                onClick={() => {
                  close();
                  onDelete(task.id);
                }}
              >
                {ru.delete}
              </button>
            </>
          )}
        </Menu>
      </div>
      {(task.due_date || task.is_blocked) && (
        <div className="task-card-meta">
          {task.due_date && (
            <span
              className={`due-chip${overdue ? ' overdue' : ''}`}
              title={overdue ? ru.overdueTitle : undefined}
            >
              {formatDue(task.due_date)}
            </span>
          )}
          {task.is_blocked && <span className="blocked-icon">{ru.blockedIcon}</span>}
        </div>
      )}
    </div>
  );
}
