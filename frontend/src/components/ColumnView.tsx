import { useDroppable } from '@dnd-kit/core';
import { SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { FormEvent, useRef, useState } from 'react';
import type { useColumnMutations, useTaskMutations } from '../api/queries';
import type { Column, ColumnWithTasks, TaskInBoard } from '../api/types';
import { fmt, ru } from '../i18n/ru';
import { ConfirmDialog } from './ConfirmDialog';
import { Menu } from './Menu';
import { TaskCard } from './TaskCard';

export const PALETTE = [
  '#6b7280', '#ef4444', '#f97316', '#eab308',
  '#22c55e', '#06b6d4', '#3b82f6', '#a855f7',
];

interface Props {
  column: ColumnWithTasks;
  allColumns: Column[];
  filter: string;
  onOpenTask: (taskId: string) => void;
  onMoveTaskTo: (taskId: string, columnId: string) => void;
  columnMut: ReturnType<typeof useColumnMutations>;
  taskMut: ReturnType<typeof useTaskMutations>;
}

export function ColumnView({
  column,
  allColumns,
  filter,
  onOpenTask,
  onMoveTaskTo,
  columnMut,
  taskMut,
}: Props) {
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteTaskId, setDeleteTaskId] = useState<string | null>(null);

  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: `col:${column.id}`,
    data: { type: 'column' },
  });
  const { setNodeRef: setDropRef } = useDroppable({
    id: `drop:${column.id}`,
    data: { type: 'column-drop', columnId: column.id },
  });

  const q = filter.trim().toLowerCase();
  const matches = (t: TaskInBoard) =>
    !q || t.title.toLowerCase().includes(q) || t.description.toLowerCase().includes(q);
  const visibleTasks = column.tasks.filter(matches);

  const n = column.tasks.length;
  const overWip = column.wip_limit !== null && n > column.wip_limit;

  return (
    <div
      ref={setNodeRef}
      className={`column${isDragging ? ' dragging' : ''}`}
      data-testid="column"
      data-column-id={column.id}
      style={{ transform: CSS.Transform.toString(transform), transition }}
    >
      <div className="column-header" {...attributes} {...listeners}>
        {column.color && <span className="column-dot" style={{ background: column.color }} />}
        <span className="column-title" data-testid="column-title">
          {column.name}
        </span>
        {column.is_final && <span className="column-final-mark">{ru.finalColumnMark}</span>}
        <span className={`column-counter${overWip ? ' over-wip' : ''}`}>
          {column.wip_limit !== null ? `${n}/${column.wip_limit}` : n}
        </span>
        <Menu buttonTestId="column-menu-button">
          {(close) => (
            <>
              <button
                data-testid="column-edit"
                onClick={() => {
                  close();
                  setEditing(true);
                }}
              >
                {ru.edit}
              </button>
              <button
                className="danger"
                data-testid="column-delete"
                onClick={() => {
                  close();
                  setDeleting(true);
                }}
              >
                {ru.delete}
              </button>
            </>
          )}
        </Menu>
      </div>

      <div className="column-tasks" ref={setDropRef}>
        <SortableContext items={column.tasks.map((t) => t.id)} strategy={verticalListSortingStrategy}>
          {visibleTasks.map((t) => (
            <TaskCard
              key={t.id}
              task={t}
              columns={allColumns}
              onOpen={onOpenTask}
              onMoveTo={onMoveTaskTo}
              onDelete={setDeleteTaskId}
            />
          ))}
        </SortableContext>
        {column.tasks.length === 0 && <div className="column-empty">{ru.columnTasksEmpty}</div>}
      </div>

      <QuickAdd onCreate={(title) => taskMut.create.mutate({ column_id: column.id, title })} />

      {editing && (
        <ColumnEditDialog
          column={column}
          onSave={(body) => {
            columnMut.update.mutate({ id: column.id, body });
            setEditing(false);
          }}
          onCancel={() => setEditing(false)}
        />
      )}
      {deleting && (
        <ColumnDeleteDialog
          column={column}
          others={allColumns.filter((c) => c.id !== column.id)}
          onAccept={(moveTasksTo) => {
            setDeleting(false);
            columnMut.remove.mutate({ id: column.id, moveTasksTo });
          }}
          onCancel={() => setDeleting(false)}
        />
      )}
      {deleteTaskId && (
        <ConfirmDialog
          title={ru.taskDeleteTitle}
          message={ru.taskDeleteWarning}
          acceptLabel={ru.delete}
          onAccept={() => {
            taskMut.remove.mutate(deleteTaskId);
            setDeleteTaskId(null);
          }}
          onCancel={() => setDeleteTaskId(null)}
        />
      )}
    </div>
  );
}

function QuickAdd({ onCreate }: { onCreate: (title: string) => void }) {
  const [title, setTitle] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const t = title.trim();
    if (t) {
      onCreate(t);
      setTitle('');
      inputRef.current?.focus();
    }
  };

  return (
    <form className="quick-add" onSubmit={submit}>
      <input
        ref={inputRef}
        data-testid="quick-add-input"
        placeholder={ru.quickAddPlaceholder}
        value={title}
        maxLength={200}
        onChange={(e) => setTitle(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Escape') {
            e.stopPropagation();
            setTitle('');
            inputRef.current?.blur();
          }
        }}
      />
      <button type="submit" data-testid="quick-add-button" title={ru.quickAddPlaceholder}>
        {ru.quickAddButton}
      </button>
    </form>
  );
}

function ColumnEditDialog({
  column,
  onSave,
  onCancel,
}: {
  column: Column;
  onSave: (body: {
    name: string;
    color: string | null;
    wip_limit: number | null;
    is_final: boolean;
  }) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(column.name);
  const [color, setColor] = useState<string | null>(column.color);
  const [wip, setWip] = useState(column.wip_limit === null ? '' : String(column.wip_limit));
  const [isFinal, setIsFinal] = useState(column.is_final);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    const wipNum = wip.trim() === '' ? null : Math.max(1, parseInt(wip, 10) || 1);
    onSave({ name: name.trim(), color, wip_limit: wipNum, is_final: isFinal });
  };

  return (
    <div className="dialog-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onCancel()}>
      <form className="dialog" onSubmit={submit}>
        <h3 className="dialog-title">{ru.columnEditTitle}</h3>
        <input
          autoFocus
          data-testid="column-name-input"
          value={name}
          maxLength={50}
          placeholder={ru.columnNamePlaceholder}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === 'Escape' && onCancel()}
        />
        <div className="field">
          <span className="field-label">{ru.columnColorLabel}</span>
          <div className="palette">
            <button
              type="button"
              className={`swatch none${color === null ? ' selected' : ''}`}
              title={ru.columnColorNone}
              onClick={() => setColor(null)}
            />
            {PALETTE.map((c) => (
              <button
                key={c}
                type="button"
                className={`swatch${color === c ? ' selected' : ''}`}
                style={{ background: c }}
                onClick={() => setColor(c)}
              />
            ))}
          </div>
        </div>
        <label className="field">
          <span className="field-label">{ru.columnWipLabel}</span>
          <input
            type="number"
            min={1}
            data-testid="column-wip-input"
            value={wip}
            onChange={(e) => setWip(e.target.value)}
          />
        </label>
        <label className="toggle">
          <input
            type="checkbox"
            data-testid="column-final-checkbox"
            checked={isFinal}
            onChange={(e) => setIsFinal(e.target.checked)}
          />
          {ru.columnFinalLabel}
        </label>
        <div className="dialog-actions">
          <button type="button" onClick={onCancel}>
            {ru.cancel}
          </button>
          <button type="submit" className="primary" data-testid="column-save" disabled={!name.trim()}>
            {ru.save}
          </button>
        </div>
      </form>
    </div>
  );
}

function ColumnDeleteDialog({
  column,
  others,
  onAccept,
  onCancel,
}: {
  column: ColumnWithTasks;
  others: Column[];
  onAccept: (moveTasksTo?: string) => void;
  onCancel: () => void;
}) {
  const hasTasks = column.tasks.length > 0;
  const [mode, setMode] = useState<'move' | 'delete'>(others.length > 0 ? 'move' : 'delete');
  const [target, setTarget] = useState(others[0]?.id ?? '');

  if (!hasTasks) {
    return (
      <ConfirmDialog
        title={ru.deleteColumnTitle}
        message={ru.deleteColumnEmptyConfirm}
        acceptLabel={ru.delete}
        onAccept={() => onAccept(undefined)}
        onCancel={onCancel}
      />
    );
  }

  return (
    <ConfirmDialog
      title={ru.deleteColumnTitle}
      message={fmt(ru.deleteColumnWithTasks, { n: column.tasks.length })}
      acceptLabel={ru.delete}
      acceptDisabled={mode === 'move' && !target}
      onAccept={() => onAccept(mode === 'move' ? target : undefined)}
      onCancel={onCancel}
    >
      <label className="toggle">
        <input
          type="radio"
          name="column-delete-mode"
          data-testid="move-tasks-radio"
          checked={mode === 'move'}
          disabled={others.length === 0}
          onChange={() => setMode('move')}
        />
        {ru.moveTasksOption}
      </label>
      <select
        data-testid="move-target-select"
        value={target}
        disabled={mode !== 'move'}
        onChange={(e) => setTarget(e.target.value)}
      >
        {others.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>
      <label className="toggle">
        <input
          type="radio"
          name="column-delete-mode"
          data-testid="delete-tasks-radio"
          checked={mode === 'delete'}
          onChange={() => setMode('delete')}
        />
        {ru.deleteTasksOption}
      </label>
    </ConfirmDialog>
  );
}
