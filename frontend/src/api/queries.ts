import {
  MutationCache,
  QueryClient,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { showToast } from '../components/Toasts';
import { fmt, ru } from '../i18n/ru';
import { api, ApiError } from './client';
import type { BoardFull, LinkType, Priority, TaskInBoard, WipWarning } from './types';

// ADR-003: оптимистичный UI; при ошибке мутации — toast с текстом сервера
// и перезагрузка доски (invalidate).
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 5_000 },
  },
  mutationCache: new MutationCache({
    onError: (error, _vars, _ctx, mutation) => {
      const msg = error instanceof ApiError ? error.message : ru.loadError;
      // Мутации со своим onError (DnD-откаты) сами показывают toast.
      if (!mutation.options.onError) showToast(msg, 'error');
    },
    onSettled: (_data, error) => {
      if (error) queryClient.invalidateQueries({ queryKey: ['board'] });
    },
  }),
});

export function warnIfWip(w: WipWarning | null) {
  if (w) {
    showToast(
      fmt(ru.wipWarningToast, { column: w.column_name, count: w.task_count, limit: w.wip_limit }),
      'warning',
    );
  }
}

// ---------- Queries ----------

export function useBoards(includeArchived: boolean) {
  return useQuery({
    queryKey: ['boards', includeArchived],
    queryFn: () => api.listBoards(includeArchived),
    // task_count меняется, пока открыта доска — список всегда перечитываем при монтировании
    staleTime: 0,
  });
}

export function useBoard(id: string) {
  return useQuery({
    queryKey: ['board', id],
    queryFn: () => api.getBoard(id),
  });
}

export function useTask(id: string | null) {
  return useQuery({
    queryKey: ['task', id],
    queryFn: () => api.getTask(id!),
    enabled: id !== null,
  });
}

// ---------- Board mutations ----------

export function useBoardMutations() {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: ['boards'] });
  return {
    create: useMutation({
      mutationFn: (body: { name: string; with_default_columns: boolean }) =>
        api.createBoard(body),
      onSuccess: invalidate,
    }),
    update: useMutation({
      mutationFn: (vars: {
        id: string;
        body: { name?: string; description?: string; archived?: boolean };
      }) => api.updateBoard(vars.id, vars.body),
      onSuccess: (_d, vars) => {
        invalidate();
        qc.invalidateQueries({ queryKey: ['board', vars.id] });
      },
    }),
    remove: useMutation({
      mutationFn: (id: string) => api.deleteBoard(id),
      onSuccess: invalidate,
    }),
  };
}

// ---------- Column / task mutations (board page) ----------

export function useColumnMutations(boardId: string) {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: ['board', boardId] });
  return {
    create: useMutation({
      mutationFn: (body: { name: string }) => api.createColumn(boardId, body),
      onSuccess: invalidate,
    }),
    update: useMutation({
      mutationFn: (vars: {
        id: string;
        body: { name?: string; color?: string | null; wip_limit?: number | null; is_final?: boolean };
      }) => api.updateColumn(vars.id, vars.body),
      onSuccess: invalidate,
    }),
    remove: useMutation({
      mutationFn: (vars: { id: string; moveTasksTo?: string }) =>
        api.deleteColumn(vars.id, vars.moveTasksTo),
      onSuccess: invalidate,
    }),
  };
}

export function useTaskMutations(boardId: string) {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: ['board', boardId] });
  return {
    create: useMutation({
      mutationFn: (body: { column_id: string; title: string }) =>
        api.createTask({ board_id: boardId, ...body }),
      onSuccess: (created) => {
        invalidate();
        warnIfWip(created.wip_warning);
      },
    }),
    update: useMutation({
      mutationFn: (vars: {
        id: string;
        body: { title?: string; description?: string; priority?: Priority; due_date?: string | null };
      }) => api.updateTask(vars.id, vars.body),
      onSuccess: (_d, vars) => {
        invalidate();
        qc.invalidateQueries({ queryKey: ['task', vars.id] });
      },
    }),
    remove: useMutation({
      mutationFn: (id: string) => api.deleteTask(id),
      onSuccess: invalidate,
    }),
  };
}

export function useLinkMutations(boardId: string, taskId: string) {
  const qc = useQueryClient();
  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['task', taskId] });
    qc.invalidateQueries({ queryKey: ['board', boardId] }); // is_blocked могло измениться
  };
  return {
    create: useMutation({
      mutationFn: (vars: { target_task_id: string; link_type: LinkType }) =>
        api.createLink({ source_task_id: taskId, ...vars }),
      onSuccess: invalidate,
    }),
    remove: useMutation({
      mutationFn: (id: string) => api.deleteLink(id),
      onSuccess: invalidate,
    }),
  };
}

// ---------- Optimistic moves (DnD + меню «Переместить в…») ----------

/** Локально применяет перемещение задачи к кэшу BoardFull. */
export function applyTaskMove(
  board: BoardFull,
  taskId: string,
  columnId: string,
  position: number,
): BoardFull {
  let moved: TaskInBoard | undefined;
  const stripped = board.columns.map((col) => {
    const idx = col.tasks.findIndex((t) => t.id === taskId);
    if (idx === -1) return col;
    moved = col.tasks[idx];
    return { ...col, tasks: col.tasks.filter((t) => t.id !== taskId) };
  });
  if (!moved) return board;
  return {
    ...board,
    columns: stripped.map((col) => {
      if (col.id !== columnId) return col;
      const tasks = [...col.tasks];
      const at = Math.max(0, Math.min(position, tasks.length));
      tasks.splice(at, 0, { ...moved!, column_id: columnId });
      return { ...col, tasks: tasks.map((t, i) => ({ ...t, position: i })) };
    }),
  };
}

/** Локально применяет перестановку колонки к кэшу BoardFull. */
export function applyColumnMove(board: BoardFull, columnId: string, position: number): BoardFull {
  const cols = [...board.columns];
  const idx = cols.findIndex((c) => c.id === columnId);
  if (idx === -1) return board;
  const [col] = cols.splice(idx, 1);
  cols.splice(Math.max(0, Math.min(position, cols.length)), 0, col);
  return { ...board, columns: cols.map((c, i) => ({ ...c, position: i })) };
}

export function useMoveTask(boardId: string) {
  const qc = useQueryClient();
  const key = ['board', boardId];
  return useMutation({
    mutationFn: (vars: { id: string; column_id: string; position: number }) =>
      api.moveTask(vars.id, { column_id: vars.column_id, position: vars.position }),
    onMutate: async (vars) => {
      await qc.cancelQueries({ queryKey: key });
      const prev = qc.getQueryData<BoardFull>(key);
      if (prev) {
        qc.setQueryData<BoardFull>(key, applyTaskMove(prev, vars.id, vars.column_id, vars.position));
      }
      return { prev };
    },
    onError: (error, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(key, ctx.prev);
      showToast(error instanceof ApiError ? error.message : ru.loadError, 'error');
    },
    onSuccess: (created) => warnIfWip(created.wip_warning),
    onSettled: () => qc.invalidateQueries({ queryKey: key }),
  });
}

export function useMoveColumn(boardId: string) {
  const qc = useQueryClient();
  const key = ['board', boardId];
  return useMutation({
    mutationFn: (vars: { id: string; position: number }) => api.moveColumn(vars.id, vars.position),
    onMutate: async (vars) => {
      await qc.cancelQueries({ queryKey: key });
      const prev = qc.getQueryData<BoardFull>(key);
      if (prev) qc.setQueryData<BoardFull>(key, applyColumnMove(prev, vars.id, vars.position));
      return { prev };
    },
    onError: (error, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(key, ctx.prev);
      showToast(error instanceof ApiError ? error.message : ru.loadError, 'error');
    },
    onSettled: () => qc.invalidateQueries({ queryKey: key }),
  });
}
