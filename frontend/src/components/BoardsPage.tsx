import { FormEvent, useState } from 'react';
import { useBoardMutations, useBoards } from '../api/queries';
import type { BoardListItem } from '../api/types';
import { fmt, ru } from '../i18n/ru';
import { ConfirmDialog } from './ConfirmDialog';
import { Menu } from './Menu';

export function BoardsPage() {
  const [showArchived, setShowArchived] = useState(false);
  const [creating, setCreating] = useState(false);
  const { data: boards, isLoading } = useBoards(showArchived);
  const mutations = useBoardMutations();

  const visible = (boards ?? []).filter((b) => showArchived || b.archived_at === null);

  return (
    <div className="page boards-page">
      <header className="page-header">
        <h1>{ru.boardsTitle}</h1>
        <label className="toggle">
          <input
            type="checkbox"
            data-testid="show-archived-toggle"
            checked={showArchived}
            onChange={(e) => setShowArchived(e.target.checked)}
          />
          {ru.showArchived}
        </label>
        <button className="primary" data-testid="new-board-button" onClick={() => setCreating(true)}>
          {ru.newBoard}
        </button>
      </header>

      {isLoading ? (
        <p className="muted">{ru.loading}</p>
      ) : visible.length === 0 ? (
        <p className="empty-state">{ru.boardsEmpty}</p>
      ) : (
        <div className="boards-grid">
          {visible.map((b) => (
            <BoardCard key={b.id} board={b} mutations={mutations} />
          ))}
        </div>
      )}

      {creating && (
        <NewBoardDialog
          onClose={() => setCreating(false)}
          onCreate={(name, empty) =>
            mutations.create.mutate(
              { name, with_default_columns: !empty },
              { onSuccess: () => setCreating(false) },
            )
          }
        />
      )}
    </div>
  );
}

function NewBoardDialog({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (name: string, empty: boolean) => void;
}) {
  const [name, setName] = useState('');
  const [empty, setEmpty] = useState(false);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (name.trim()) onCreate(name.trim(), empty);
  };

  return (
    <div className="dialog-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <form className="dialog" onSubmit={submit}>
        <h3 className="dialog-title">{ru.newBoard}</h3>
        <input
          autoFocus
          data-testid="board-name-input"
          placeholder={ru.boardNamePlaceholder}
          value={name}
          maxLength={100}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === 'Escape' && onClose()}
        />
        <label className="toggle">
          <input
            type="checkbox"
            data-testid="board-empty-checkbox"
            checked={empty}
            onChange={(e) => setEmpty(e.target.checked)}
          />
          {ru.boardEmptyCheckbox}
        </label>
        <div className="dialog-actions">
          <button type="button" onClick={onClose}>
            {ru.cancel}
          </button>
          <button
            type="submit"
            className="primary"
            data-testid="board-create-submit"
            disabled={!name.trim()}
          >
            {ru.create}
          </button>
        </div>
      </form>
    </div>
  );
}

function BoardCard({
  board,
  mutations,
}: {
  board: BoardListItem;
  mutations: ReturnType<typeof useBoardMutations>;
}) {
  const [renaming, setRenaming] = useState(false);
  const [name, setName] = useState(board.name);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const archived = board.archived_at !== null;

  const commitRename = () => {
    setRenaming(false);
    const trimmed = name.trim();
    if (trimmed && trimmed !== board.name) {
      mutations.update.mutate({ id: board.id, body: { name: trimmed } });
    } else {
      setName(board.name);
    }
  };

  return (
    <div
      className={`board-card${archived ? ' archived' : ''}`}
      data-testid="board-card"
      onClick={() => !renaming && (window.location.hash = `#/board/${board.id}`)}
    >
      <div className="board-card-top">
        {renaming ? (
          <input
            autoFocus
            className="inline-input"
            value={name}
            maxLength={100}
            placeholder={ru.boardRenamePlaceholder}
            onClick={(e) => e.stopPropagation()}
            onChange={(e) => setName(e.target.value)}
            onBlur={commitRename}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commitRename();
              if (e.key === 'Escape') {
                setName(board.name);
                setRenaming(false);
              }
            }}
          />
        ) : (
          <h2 className="board-card-name">{board.name}</h2>
        )}
        <Menu buttonTestId="board-menu-button">
          {(close) => (
            <>
              <button
                data-testid="board-rename"
                onClick={() => {
                  close();
                  setRenaming(true);
                }}
              >
                {ru.rename}
              </button>
              <button
                data-testid="board-archive"
                onClick={() => {
                  close();
                  mutations.update.mutate({ id: board.id, body: { archived: !archived } });
                }}
              >
                {archived ? ru.unarchive : ru.archive}
              </button>
              <button
                className="danger"
                data-testid="board-delete"
                onClick={() => {
                  close();
                  setConfirmDelete(true);
                }}
              >
                {ru.delete}
              </button>
            </>
          )}
        </Menu>
      </div>
      {board.description && <p className="board-card-desc">{board.description}</p>}
      <p className="board-card-count">
        {ru.taskCountLabel} {board.task_count}
        {archived && <span className="archived-badge"> · {ru.archivedBadge}</span>}
      </p>

      {confirmDelete && (
        <div onClick={(e) => e.stopPropagation()}>
          <ConfirmDialog
            title={ru.deleteBoardTitle}
            message={fmt(ru.deleteBoardTasksWarning, { n: board.task_count })}
            acceptLabel={ru.delete}
            onAccept={() => {
              setConfirmDelete(false);
              mutations.remove.mutate(board.id);
            }}
            onCancel={() => setConfirmDelete(false)}
          />
        </div>
      )}
    </div>
  );
}
