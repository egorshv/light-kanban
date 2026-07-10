import { ru } from '../i18n/ru';
import type {
  Board, BoardFull, BoardListItem, Column, Link, LinkType, Priority,
  Task, TaskCreated, TaskWithLinks,
} from './types';

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const BASE = '/api/v1';

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const token = localStorage.getItem('kanban_token');
  if (token) headers['Authorization'] = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(BASE + path, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError('NETWORK_ERROR', ru.networkError, 0);
  }

  if (!res.ok) {
    let code = 'UNKNOWN';
    let message = ru.loadError;
    try {
      const data = await res.json();
      if (data?.error) {
        code = data.error.code ?? code;
        message = data.error.message ?? message;
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(code, message, res.status);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  // Boards
  listBoards: (includeArchived: boolean) =>
    request<BoardListItem[]>('GET', `/boards${includeArchived ? '?include_archived=true' : ''}`),
  createBoard: (body: { name: string; description?: string; with_default_columns?: boolean }) =>
    request<Board>('POST', '/boards', body),
  getBoard: (id: string) => request<BoardFull>('GET', `/boards/${id}`),
  updateBoard: (id: string, body: { name?: string; description?: string; archived?: boolean }) =>
    request<Board>('PATCH', `/boards/${id}`, body),
  deleteBoard: (id: string) => request<void>('DELETE', `/boards/${id}`),

  // Columns
  createColumn: (
    boardId: string,
    body: { name: string; color?: string; wip_limit?: number; is_final?: boolean },
  ) => request<Column>('POST', `/boards/${boardId}/columns`, body),
  updateColumn: (
    id: string,
    body: { name?: string; color?: string | null; wip_limit?: number | null; is_final?: boolean },
  ) => request<Column>('PATCH', `/columns/${id}`, body),
  moveColumn: (id: string, position: number) =>
    request<Column>('POST', `/columns/${id}/move`, { position }),
  deleteColumn: (id: string, moveTasksTo?: string) =>
    request<void>(
      'DELETE',
      `/columns/${id}${moveTasksTo ? `?move_tasks_to=${encodeURIComponent(moveTasksTo)}` : ''}`,
    ),

  // Tasks
  createTask: (body: {
    board_id: string;
    column_id: string;
    title: string;
    description?: string;
    priority?: Priority;
    due_date?: string;
  }) => request<TaskCreated>('POST', '/tasks', body),
  getTask: (id: string) => request<TaskWithLinks>('GET', `/tasks/${id}`),
  updateTask: (
    id: string,
    body: { title?: string; description?: string; priority?: Priority; due_date?: string | null },
  ) => request<Task>('PATCH', `/tasks/${id}`, body),
  moveTask: (id: string, body: { column_id: string; position: number }) =>
    request<TaskCreated>('POST', `/tasks/${id}/move`, body),
  deleteTask: (id: string) => request<void>('DELETE', `/tasks/${id}`),
  searchTasks: (boardId: string, q: string) =>
    request<Task[]>('GET', `/boards/${boardId}/tasks?q=${encodeURIComponent(q)}`),

  // Links
  createLink: (body: { source_task_id: string; target_task_id: string; link_type: LinkType }) =>
    request<Link>('POST', '/links', body),
  deleteLink: (id: string) => request<void>('DELETE', `/links/${id}`),
};
