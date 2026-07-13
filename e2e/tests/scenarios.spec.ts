import { expect, Page, test } from '@playwright/test';

// 4–5 сценариев §10: доска → колонка → задача → переместить → связать → удалить доску

const uniq = () => `${Date.now()}-${Math.floor(Math.random() * 1000)}`;

// Auth обязательна: уникальный пользователь на тест ⇒ пустой список досок и полная изоляция.
test.beforeEach(async ({ page, request }) => {
  const res = await request.post('/api/v1/auth/register', {
    data: { email: `e2e-${uniq()}@test.ru`, password: 'password1' },
  });
  const { token } = await res.json();
  await page.addInitScript((t: string) => localStorage.setItem('kanban_token', t), token);
});

// Чистый контекст (без initScript с токеном): полный цикл регистрация → logout.
test('регистрация через UI и выход', async ({ browser }) => {
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  await page.goto('/');
  await expect(page.getByTestId('auth-email-input')).toBeVisible();
  await page.getByTestId('auth-mode-toggle').click();
  await page.getByTestId('auth-email-input').fill(`ui-${uniq()}@test.ru`);
  await page.getByTestId('auth-password-input').fill('password1');
  await page.getByTestId('auth-submit').click();
  await expect(page.getByTestId('new-board-button')).toBeVisible();
  await page.getByTestId('logout-button').click();
  await expect(page.getByTestId('auth-email-input')).toBeVisible();
  await ctx.close();
});

async function createBoard(page: Page, name: string) {
  await page.goto('/');
  await page.getByTestId('new-board-button').click();
  await page.getByTestId('board-name-input').fill(name);
  await page.getByTestId('board-create-submit').click();
  await expect(page.getByTestId('board-card').filter({ hasText: name })).toBeVisible();
}

async function openBoard(page: Page, name: string) {
  await page.getByTestId('board-card').filter({ hasText: name }).click();
  await expect(page.getByTestId('board-title')).toContainText(name);
}

async function quickAdd(page: Page, columnIndex: number, title: string) {
  const column = page.getByTestId('column').nth(columnIndex);
  const button = column.getByTestId('quick-add-button');
  if (await button.count()) {
    await button.click();
  }
  const input = column.getByTestId('quick-add-input');
  await input.fill(title);
  await input.press('Enter');
  await expect(column.getByTestId('task-card').filter({ hasText: title })).toBeVisible();
}

test('создание доски с колонками по умолчанию', async ({ page }) => {
  const name = `Доска ${uniq()}`;
  await createBoard(page, name);
  await openBoard(page, name);
  await expect(page.getByTestId('column')).toHaveCount(3);
  await expect(page.getByTestId('column-title').nth(0)).toContainText('Backlog');
  await expect(page.getByTestId('column-title').nth(1)).toContainText('В работе');
  await expect(page.getByTestId('column-title').nth(2)).toContainText('Готово');
});

test('новая колонка, быстрое создание задач, поиск', async ({ page }) => {
  const name = `Доска ${uniq()}`;
  await createBoard(page, name);
  await openBoard(page, name);

  await page.getByTestId('add-column-button').click();
  await page.getByTestId('column-name-input').fill('Ревью');
  await page.getByTestId('column-create-submit').click();
  await expect(page.getByTestId('column')).toHaveCount(4);

  await quickAdd(page, 0, 'Купить хлеб');
  await quickAdd(page, 0, 'Помыть посуду');

  await page.getByTestId('search-input').fill('хлеб');
  await expect(page.getByTestId('task-card').filter({ hasText: 'Купить хлеб' })).toBeVisible();
  await expect(page.getByTestId('task-card').filter({ hasText: 'Помыть посуду' })).toBeHidden();
});

test('перемещение задачи в финальную колонку через меню', async ({ page }) => {
  const name = `Доска ${uniq()}`;
  await createBoard(page, name);
  await openBoard(page, name);
  await quickAdd(page, 0, 'Задача Икс');

  const card = page.getByTestId('task-card').filter({ hasText: 'Задача Икс' });
  await card.getByTestId('task-menu-button').click();
  await page.getByTestId('task-move-option').filter({ hasText: 'Готово' }).click();

  const done = page.getByTestId('column').nth(2);
  await expect(done.getByTestId('task-card').filter({ hasText: 'Задача Икс' })).toBeVisible();
});

test('связь blocks, запрет цикла, удаление связи', async ({ page }) => {
  const name = `Доска ${uniq()}`;
  await createBoard(page, name);
  await openBoard(page, name);
  await quickAdd(page, 0, 'Альфа');
  await quickAdd(page, 0, 'Бета');

  // Альфа блокирует Бету
  await page.getByTestId('task-card').filter({ hasText: 'Альфа' }).click();
  const panel = page.getByTestId('task-panel');
  await panel.getByTestId('link-type-select').selectOption('blocks');
  await panel.getByTestId('link-target-input').fill('Бета');
  await page.getByTestId('link-target-option').filter({ hasText: 'Бета' }).click();
  await panel.getByTestId('link-add-button').click();
  await expect(panel.getByTestId('link-item')).toHaveCount(1);
  await page.getByTestId('panel-close').click();

  // обратная связь создала бы цикл — сервер отвечает 422, UI показывает ошибку
  await page.getByTestId('task-card').filter({ hasText: 'Бета' }).click();
  await panel.getByTestId('link-type-select').selectOption('blocks');
  await panel.getByTestId('link-target-input').fill('Альфа');
  await page.getByTestId('link-target-option').filter({ hasText: 'Альфа' }).click();
  await panel.getByTestId('link-add-button').click();
  await expect(page.getByTestId('toast').filter({ hasText: 'цикл' })).toBeVisible();

  // связь можно удалить из карточки любой из задач (US-D3)
  await panel.getByTestId('link-item').getByTestId('link-remove-button').click();
  await expect(panel.getByTestId('link-item')).toHaveCount(0);
});

test('удаление доски с подтверждением и числом задач', async ({ page }) => {
  const name = `Доска ${uniq()}`;
  await createBoard(page, name);
  await openBoard(page, name);
  await quickAdd(page, 0, 'Единственная задача');

  await page.getByTestId('back-to-boards').click();
  const card = page.getByTestId('board-card').filter({ hasText: name });
  await card.getByTestId('board-menu-button').click();
  await page.getByTestId('board-delete').click();

  const dialog = page.getByTestId('confirm-dialog');
  await expect(dialog).toContainText('1'); // «Будут удалены N задач»
  await dialog.getByTestId('confirm-accept').click();
  await expect(card).toHaveCount(0);
});
