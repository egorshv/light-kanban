// ADR-008: все строки UI — в одном плоском типизированном словаре.
export const ru = {
  // Общее
  appTitle: 'light-kanban',
  loading: 'Загрузка…',
  loadError: 'Не удалось загрузить данные',
  networkError: 'Ошибка сети. Проверьте соединение.',
  save: 'Сохранить',
  cancel: 'Отмена',
  delete: 'Удалить',
  confirm: 'Подтвердить',
  close: 'Закрыть',
  rename: 'Переименовать',
  edit: 'Редактировать',

  // Список досок
  boardsTitle: 'Доски',
  newBoard: '＋ Новая доска',
  boardNamePlaceholder: 'Название доски',
  boardEmptyCheckbox: 'Создать пустую',
  create: 'Создать',
  showArchived: 'Показать архивные',
  archive: 'Архивировать',
  unarchive: 'Разархивировать',
  archivedBadge: 'В архиве',
  taskCountLabel: 'Задач:',
  deleteBoardTitle: 'Удалить доску?',
  deleteBoardTasksWarning: 'Будут удалены {n} задач',
  boardsEmpty: 'Создайте первую доску, чтобы начать работу',
  boardRenamePlaceholder: 'Новое название',

  // Доска
  backToBoards: '← Доски',
  searchPlaceholder: 'Поиск задач…',
  addColumn: '＋ Колонка',
  columnNamePlaceholder: 'Название колонки',
  columnsEmpty: 'Создайте первую колонку, чтобы добавлять задачи',
  columnTasksEmpty: 'Нет задач',
  quickAddPlaceholder: 'Новая задача…',
  quickAddButton: '＋',
  finalColumnMark: '✓',

  // Колонка: редактирование / удаление
  columnEditTitle: 'Колонка',
  columnColorLabel: 'Цвет',
  columnColorNone: 'Без цвета',
  columnWipLabel: 'WIP-лимит',
  columnFinalLabel: 'Финальная колонка (задачи считаются завершёнными)',
  deleteColumnTitle: 'Удалить колонку?',
  deleteColumnEmptyConfirm: 'Колонка пуста и будет удалена.',
  deleteColumnWithTasks: 'В колонке {n} задач. Что с ними сделать?',
  moveTasksOption: 'Перенести задачи в другую колонку',
  deleteTasksOption: 'Удалить задачи вместе с колонкой',

  // Задача
  taskDeleteTitle: 'Удалить задачу?',
  taskDeleteWarning: 'Задача и все её связи будут удалены.',
  moveTo: 'Переместить в…',
  taskTitlePlaceholder: 'Заголовок задачи',
  descriptionLabel: 'Описание',
  descriptionPlaceholder: 'Описание (markdown)…',
  descriptionEmpty: 'Нажмите, чтобы добавить описание',
  priorityLabel: 'Приоритет',
  priorityLow: 'Низкий',
  priorityNormal: 'Обычный',
  priorityHigh: 'Высокий',
  priorityUrgent: 'Срочный',
  dueDateLabel: 'Срок',
  createdLabel: 'Создана',
  completedLabel: 'Завершена',

  // WIP
  wipWarningToast: 'Лимит WIP превышен: {column} {count}/{limit}',

  // Связи
  linksTitle: 'Связи',
  linkBlocksOut: 'Блокирует',
  linkBlocksIn: 'Заблокирована задачей',
  linkSubtaskOut: 'Подзадача',
  linkSubtaskIn: 'Содержит',
  linkRelates: 'Связана с',
  linkDuplicatesOut: 'Дублирует',
  linkDuplicatesIn: 'Дублируется',
  linkTypeBlocks: 'блокирует',
  linkTypeSubtaskOf: 'подзадача',
  linkTypeRelatesTo: 'связана с',
  linkTypeDuplicates: 'дублирует',
  linkTargetPlaceholder: 'Найти задачу…',
  linkAdd: 'Добавить',
  linkRemove: '×',
  linkNoResults: 'Ничего не найдено',
  linksEmpty: 'Связей пока нет',

  // Индикаторы
  blockedIcon: '🔒',
  overdueTitle: 'Просрочено',
} as const;

export type RuKey = keyof typeof ru;

/** Подстановка {placeholder}-значений в строку словаря. */
export function fmt(template: string, params: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, k) => String(params[k] ?? ''));
}
