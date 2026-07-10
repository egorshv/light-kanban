import {
  closestCorners,
  DndContext,
  DragEndEvent,
  DragOverEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import { horizontalListSortingStrategy, SortableContext } from '@dnd-kit/sortable';
import { FormEvent, useEffect, useRef, useState } from 'react';
import {
  useBoard,
  useBoardMutations,
  useColumnMutations,
  useMoveColumn,
  useMoveTask,
  useTaskMutations,
} from '../api/queries';
import { applyTaskMove } from '../api/queries';
import type { BoardFull, TaskInBoard } from '../api/types';
import { ru } from '../i18n/ru';
import { ColumnView } from './ColumnView';
import { TaskPanel } from './TaskPanel';

export function BoardPage({ boardId }: { boardId: string }) {
  const { data: boardData, isLoading, isError } = useBoard(boardId);
  const boardMut = useBoardMutations();
  const columnMut = useColumnMutations(boardId);
  const taskMut = useTaskMutations(boardId);
  const moveTask = useMoveTask(boardId);
  const moveColumn = useMoveColumn(boardId);

  const [filter, setFilter] = useState('');
  const [openTaskId, setOpenTaskId] = useState<string | null>(null);
  const [addingColumn, setAddingColumn] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);

  // Локальная копия доски на время перетаскивания (живой индикатор «куда встанет»).
  const [dragBoard, setDragBoard] = useState<BoardFull | null>(null);
  const [activeTask, setActiveTask] = useState<TaskInBoard | null>(null);
  const dragOrigin = useRef<{ columnId: string; index: number } | null>(null);

  const board = dragBoard ?? boardData;

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  // Хоткеи: N — быстрая задача в первой колонке, / — поиск. Esc обрабатывают панель/диалоги.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (
        t.tagName === 'INPUT' ||
        t.tagName === 'TEXTAREA' ||
        t.tagName === 'SELECT' ||
        t.isContentEditable
      )
        return;
      if (e.key === '/') {
        e.preventDefault();
        searchRef.current?.focus();
      } else if (e.key.toLowerCase() === 'n' || e.key.toLowerCase() === 'т') {
        e.preventDefault();
        document.querySelector<HTMLInputElement>('[data-testid="quick-add-input"]')?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  if (isLoading) return <div className="page">{ru.loading}</div>;
  if (isError || !board) return <div className="page">{ru.loadError}</div>;

  const findTask = (b: BoardFull, id: string) => {
    for (const col of b.columns) {
      const idx = col.tasks.findIndex((t) => t.id === id);
      if (idx !== -1) return { column: col, index: idx, task: col.tasks[idx] };
    }
    return null;
  };

  const onDragStart = (e: DragStartEvent) => {
    if (e.active.data.current?.type === 'task' && boardData) {
      const loc = findTask(boardData, String(e.active.id));
      if (loc) {
        setActiveTask(loc.task);
        dragOrigin.current = { columnId: loc.column.id, index: loc.index };
        setDragBoard(boardData);
      }
    }
  };

  const onDragOver = (e: DragOverEvent) => {
    if (e.active.data.current?.type !== 'task' || !e.over) return;
    setDragBoard((prev) => {
      if (!prev) return prev;
      const activeId = String(e.active.id);
      const overId = String(e.over!.id);
      let targetCol: string | null = null;
      let targetIdx = 0;
      if (overId.startsWith('drop:')) {
        targetCol = overId.slice(5);
        targetIdx = prev.columns.find((c) => c.id === targetCol)?.tasks.length ?? 0;
      } else if (!overId.startsWith('col:') && overId !== activeId) {
        const loc = findTask(prev, overId);
        if (loc) {
          targetCol = loc.column.id;
          targetIdx = loc.index;
        }
      }
      if (!targetCol) return prev;
      const cur = findTask(prev, activeId);
      if (cur && cur.column.id === targetCol && cur.index === targetIdx) return prev;
      return applyTaskMove(prev, activeId, targetCol, targetIdx);
    });
  };

  const onDragEnd = (e: DragEndEvent) => {
    const type = e.active.data.current?.type;
    if (type === 'task') {
      const final = dragBoard && findTask(dragBoard, String(e.active.id));
      setDragBoard(null);
      setActiveTask(null);
      if (
        final &&
        dragOrigin.current &&
        (final.column.id !== dragOrigin.current.columnId || final.index !== dragOrigin.current.index)
      ) {
        moveTask.mutate({
          id: String(e.active.id),
          column_id: final.column.id,
          position: final.index,
        });
      }
      dragOrigin.current = null;
    } else if (type === 'column' && e.over && boardData) {
      const activeId = String(e.active.id).slice(4);
      const overId = String(e.over.id).startsWith('col:')
        ? String(e.over.id).slice(4)
        : e.over.data.current?.columnId;
      if (!overId || overId === activeId) return;
      const newIndex = boardData.columns.findIndex((c) => c.id === overId);
      if (newIndex !== -1) moveColumn.mutate({ id: activeId, position: newIndex });
    }
  };

  const onDragCancel = () => {
    setDragBoard(null);
    setActiveTask(null);
    dragOrigin.current = null;
  };

  const moveTaskToEnd = (taskId: string, columnId: string) => {
    const target = board.columns.find((c) => c.id === columnId);
    if (target) moveTask.mutate({ id: taskId, column_id: columnId, position: target.tasks.length });
  };

  return (
    <div className="page board-page">
      <header className="board-header">
        <a href="#/" data-testid="back-to-boards" className="back-link">
          {ru.backToBoards}
        </a>
        <BoardTitle
          name={board.name}
          onRename={(name) => boardMut.update.mutate({ id: boardId, body: { name } })}
        />
        <input
          ref={searchRef}
          className="search-input"
          data-testid="search-input"
          placeholder={ru.searchPlaceholder}
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              e.stopPropagation();
              setFilter('');
              e.currentTarget.blur();
            }
          }}
        />
        {addingColumn ? (
          <AddColumnForm
            onCreate={(name) =>
              columnMut.create.mutate({ name }, { onSuccess: () => setAddingColumn(false) })
            }
            onCancel={() => setAddingColumn(false)}
          />
        ) : (
          <button data-testid="add-column-button" onClick={() => setAddingColumn(true)}>
            {ru.addColumn}
          </button>
        )}
      </header>

      {board.columns.length === 0 ? (
        <p className="empty-state">{ru.columnsEmpty}</p>
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={onDragStart}
          onDragOver={onDragOver}
          onDragEnd={onDragEnd}
          onDragCancel={onDragCancel}
        >
          <div className="columns-strip">
            <SortableContext
              items={board.columns.map((c) => `col:${c.id}`)}
              strategy={horizontalListSortingStrategy}
            >
              {board.columns.map((col) => (
                <ColumnView
                  key={col.id}
                  column={col}
                  allColumns={board.columns}
                  filter={filter}
                  onOpenTask={setOpenTaskId}
                  onMoveTaskTo={moveTaskToEnd}
                  columnMut={columnMut}
                  taskMut={taskMut}
                />
              ))}
            </SortableContext>
          </div>
          <DragOverlay>
            {activeTask && (
              <div className={`task-card overlay prio-${activeTask.priority}`}>
                <span className="task-card-title">{activeTask.title}</span>
              </div>
            )}
          </DragOverlay>
        </DndContext>
      )}

      {openTaskId && (
        <TaskPanel
          taskId={openTaskId}
          boardId={boardId}
          taskMut={taskMut}
          onClose={() => setOpenTaskId(null)}
        />
      )}
    </div>
  );
}

function BoardTitle({ name, onRename }: { name: string; onRename: (name: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(name);

  if (!editing) {
    return (
      <h1
        className="board-title"
        data-testid="board-title"
        title={ru.rename}
        onClick={() => {
          setValue(name);
          setEditing(true);
        }}
      >
        {name}
      </h1>
    );
  }
  const commit = () => {
    setEditing(false);
    const v = value.trim();
    if (v && v !== name) onRename(v);
  };
  return (
    <input
      autoFocus
      className="inline-input board-title-input"
      data-testid="board-title"
      value={value}
      maxLength={100}
      onChange={(e) => setValue(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === 'Enter') commit();
        if (e.key === 'Escape') {
          e.stopPropagation();
          setEditing(false);
        }
      }}
    />
  );
}

function AddColumnForm({
  onCreate,
  onCancel,
}: {
  onCreate: (name: string) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState('');
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (name.trim()) onCreate(name.trim());
  };
  return (
    <form className="add-column-form" onSubmit={submit}>
      <input
        autoFocus
        data-testid="column-name-input"
        placeholder={ru.columnNamePlaceholder}
        value={name}
        maxLength={50}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Escape') {
            e.stopPropagation();
            onCancel();
          }
        }}
      />
      <button type="submit" data-testid="column-create-submit" disabled={!name.trim()}>
        {ru.create}
      </button>
    </form>
  );
}
