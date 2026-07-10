import { useQuery } from '@tanstack/react-query';
import DOMPurify from 'dompurify';
import { marked } from 'marked';
import { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import { useLinkMutations, useTask, useTaskMutations } from '../api/queries';
import type { LinkType, Priority, TaskLink, TaskWithLinks } from '../api/types';
import { ru } from '../i18n/ru';
import { ConfirmDialog } from './ConfirmDialog';

interface Props {
  taskId: string;
  boardId: string;
  taskMut: ReturnType<typeof useTaskMutations>;
  onClose: () => void;
}

export function TaskPanel({ taskId, boardId, taskMut, onClose }: Props) {
  const { data: task } = useTask(taskId);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <aside className="task-panel" data-testid="task-panel">
      <button className="panel-close" data-testid="panel-close" onClick={onClose} title={ru.close}>
        ×
      </button>
      {task ? (
        <PanelBody key={task.id} task={task} boardId={boardId} taskMut={taskMut} onClose={onClose} />
      ) : (
        <p className="muted">{ru.loading}</p>
      )}
    </aside>
  );
}

type PatchBody = { title?: string; description?: string; priority?: Priority; due_date?: string | null };

function PanelBody({
  task,
  boardId,
  taskMut,
  onClose,
}: {
  task: TaskWithLinks;
  boardId: string;
  taskMut: ReturnType<typeof useTaskMutations>;
  onClose: () => void;
}) {
  const [title, setTitle] = useState(task.title);
  const [description, setDescription] = useState(task.description);
  const [confirmDelete, setConfirmDelete] = useState(false);

  // Автосохранение: debounce ~500 мс на поле + немедленный flush на blur.
  const pending = useRef<PatchBody>({});
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const update = taskMut.update;

  const flush = () => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    const body = pending.current;
    pending.current = {};
    if (Object.keys(body).length > 0) update.mutate({ id: task.id, body });
  };
  const queue = (body: PatchBody) => {
    pending.current = { ...pending.current, ...body };
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(flush, 500);
  };
  // flush при размонтировании (закрытие панели)
  useEffect(() => flush, []); // eslint-disable-line react-hooks/exhaustive-deps

  const rendered = description.trim()
    ? DOMPurify.sanitize(marked.parse(description, { async: false }))
    : '';

  return (
    <div className="panel-body">
      <input
        className="panel-title"
        data-testid="task-title-input"
        value={title}
        maxLength={200}
        placeholder={ru.taskTitlePlaceholder}
        onChange={(e) => {
          setTitle(e.target.value);
          if (e.target.value.trim()) queue({ title: e.target.value.trim() });
        }}
        onBlur={flush}
      />

      <label className="field">
        <span className="field-label">{ru.priorityLabel}</span>
        <select
          data-testid="task-priority-select"
          value={task.priority}
          onChange={(e) => update.mutate({ id: task.id, body: { priority: e.target.value as Priority } })}
        >
          <option value="low">{ru.priorityLow}</option>
          <option value="normal">{ru.priorityNormal}</option>
          <option value="high">{ru.priorityHigh}</option>
          <option value="urgent">{ru.priorityUrgent}</option>
        </select>
      </label>

      <label className="field">
        <span className="field-label">{ru.dueDateLabel}</span>
        <input
          type="date"
          data-testid="task-due-input"
          value={task.due_date ?? ''}
          onChange={(e) =>
            update.mutate({ id: task.id, body: { due_date: e.target.value || null } })
          }
        />
      </label>

      <div className="field">
        <span className="field-label">{ru.descriptionLabel}</span>
        <textarea
          data-testid="task-description-input"
          rows={6}
          placeholder={ru.descriptionPlaceholder}
          value={description}
          onChange={(e) => {
            setDescription(e.target.value);
            queue({ description: e.target.value });
          }}
          onBlur={flush}
        />
        {rendered && (
          <div className="markdown-preview" dangerouslySetInnerHTML={{ __html: rendered }} />
        )}
      </div>

      <LinksSection task={task} boardId={boardId} />

      <div className="panel-footer">
        {task.completed_at && (
          <span className="muted">
            {ru.completedLabel}: {task.completed_at.slice(0, 10)}
          </span>
        )}
        <button className="danger" onClick={() => setConfirmDelete(true)}>
          {ru.delete}
        </button>
      </div>

      {confirmDelete && (
        <ConfirmDialog
          title={ru.taskDeleteTitle}
          message={ru.taskDeleteWarning}
          acceptLabel={ru.delete}
          onAccept={() => {
            setConfirmDelete(false);
            taskMut.remove.mutate(task.id, { onSuccess: onClose });
          }}
          onCancel={() => setConfirmDelete(false)}
        />
      )}
    </div>
  );
}

// ---------- Связи ----------

function linkLabel(link: TaskLink): string {
  switch (link.link_type) {
    case 'blocks':
      return link.direction === 'out' ? ru.linkBlocksOut : ru.linkBlocksIn;
    case 'subtask_of':
      return link.direction === 'out' ? ru.linkSubtaskOut : ru.linkSubtaskIn;
    case 'relates_to':
      return ru.linkRelates;
    case 'duplicates':
      return link.direction === 'out' ? ru.linkDuplicatesOut : ru.linkDuplicatesIn;
  }
}

function LinksSection({ task, boardId }: { task: TaskWithLinks; boardId: string }) {
  const linkMut = useLinkMutations(boardId, task.id);

  const groups = new Map<string, TaskLink[]>();
  for (const link of task.links) {
    const label = linkLabel(link);
    groups.set(label, [...(groups.get(label) ?? []), link]);
  }

  return (
    <div className="links-section">
      <h3>{ru.linksTitle}</h3>
      {task.links.length === 0 && <p className="muted">{ru.linksEmpty}</p>}
      {[...groups.entries()].map(([label, links]) => (
        <div key={label} className="link-group">
          <div className="link-group-label">{label}</div>
          {links.map((link) => (
            <div key={link.id} className="link-item" data-testid="link-item">
              <span className={link.other_task.completed_at ? 'link-done' : ''}>
                {link.other_task.title}
              </span>
              <button
                className="link-remove"
                data-testid="link-remove-button"
                title={ru.delete}
                onClick={() => linkMut.remove.mutate(link.id)}
              >
                {ru.linkRemove}
              </button>
            </div>
          ))}
        </div>
      ))}
      <AddLinkForm
        boardId={boardId}
        selfId={task.id}
        onAdd={(targetId, type) => linkMut.create.mutate({ target_task_id: targetId, link_type: type })}
      />
    </div>
  );
}

function AddLinkForm({
  boardId,
  selfId,
  onAdd,
}: {
  boardId: string;
  selfId: string;
  onAdd: (targetId: string, type: LinkType) => void;
}) {
  const [type, setType] = useState<LinkType>('blocks');
  const [query, setQuery] = useState('');
  const [debounced, setDebounced] = useState('');
  const [target, setTarget] = useState<{ id: string; title: string } | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(query.trim()), 250);
    return () => clearTimeout(t);
  }, [query]);

  const { data: results } = useQuery({
    queryKey: ['taskSearch', boardId, debounced],
    queryFn: () => api.searchTasks(boardId, debounced),
    enabled: debounced.length > 0,
  });

  const options = (results ?? []).filter((t) => t.id !== selfId);

  return (
    <div className="add-link-form">
      <select
        data-testid="link-type-select"
        value={type}
        onChange={(e) => setType(e.target.value as LinkType)}
      >
        <option value="blocks">{ru.linkTypeBlocks}</option>
        <option value="subtask_of">{ru.linkTypeSubtaskOf}</option>
        <option value="relates_to">{ru.linkTypeRelatesTo}</option>
        <option value="duplicates">{ru.linkTypeDuplicates}</option>
      </select>
      <div className="autocomplete">
        <input
          data-testid="link-target-input"
          placeholder={ru.linkTargetPlaceholder}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setTarget(null);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === 'Escape' && open) {
              e.stopPropagation();
              setOpen(false);
            }
          }}
        />
        {open && debounced.length > 0 && !target && (
          <div className="autocomplete-list">
            {options.length === 0 ? (
              <div className="muted autocomplete-empty">{ru.linkNoResults}</div>
            ) : (
              options.map((t) => (
                <button
                  key={t.id}
                  data-testid="link-target-option"
                  onClick={() => {
                    setTarget({ id: t.id, title: t.title });
                    setQuery(t.title);
                    setOpen(false);
                  }}
                >
                  {t.title}
                </button>
              ))
            )}
          </div>
        )}
      </div>
      <button
        data-testid="link-add-button"
        disabled={!target}
        onClick={() => {
          if (target) {
            onAdd(target.id, type);
            setQuery('');
            setTarget(null);
          }
        }}
      >
        {ru.linkAdd}
      </button>
    </div>
  );
}
