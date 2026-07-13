export type Priority = 'low' | 'normal' | 'high' | 'urgent';
export type LinkType = 'blocks' | 'subtask_of' | 'relates_to' | 'duplicates';

export interface User {
  id: string;
  email: string;
  name: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface Board {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface BoardListItem extends Board {
  task_count: number;
}

export interface Column {
  id: string;
  board_id: string;
  name: string;
  position: number;
  wip_limit: number | null;
  color: string | null;
  is_final: boolean;
}

export interface Task {
  id: string;
  board_id: string;
  column_id: string;
  title: string;
  description: string;
  position: number;
  priority: Priority;
  due_date: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface TaskInBoard extends Task {
  is_blocked: boolean;
}

export interface ColumnWithTasks extends Column {
  tasks: TaskInBoard[]; // sorted by position
}

export interface BoardFull extends Board {
  columns: ColumnWithTasks[]; // sorted by position
}

export interface WipWarning {
  column_id: string;
  column_name: string;
  wip_limit: number;
  task_count: number;
}

export interface TaskCreated extends Task {
  wip_warning: WipWarning | null;
}

export interface LinkedTaskRef {
  id: string;
  title: string;
  board_id: string;
  completed_at: string | null;
}

export interface TaskLink {
  id: string;
  link_type: LinkType;
  direction: 'out' | 'in';
  created_at: string;
  other_task: LinkedTaskRef;
}

export interface TaskWithLinks extends Task {
  links: TaskLink[];
}

export interface Link {
  id: string;
  source_task_id: string;
  target_task_id: string;
  link_type: LinkType;
  created_at: string;
}
