import { expect, test } from '@playwright/test';

async function nurseLogin(page: import('@playwright/test').Page) {
  await page.goto('/auth/login');
  for (const digit of ['2', '4', '6', '8']) await page.getByRole('button', { name: digit, exact: true }).click();
  await page.getByRole('button', { name: 'Login' }).click();
  await expect(page).toHaveURL(/\/nurse\/queue/);
}

test('patient can log in and reach the authenticated dashboard', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Phone number').fill('+2348012345678');
  await page.getByLabel('Password').fill('Password123!');
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText(/Welcome back/)).toBeVisible();
});

test('specialist and hospital login surfaces establish role sessions', async ({ page }) => {
  await page.goto('/specialist/login');
  await page.getByLabel('Email address').fill('dr.ada@example.com');
  await page.getByLabel('Password').fill('Password123!');
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page).toHaveURL(/\/specialist\/dashboard/);

  await page.context().clearCookies();
  await page.goto('/hospital/login');
  await page.getByLabel('Hospital password').fill('Password123!');
  await page.getByRole('button', { name: 'Enter Hospital Workspace' }).click();
  await expect(page).toHaveURL(/\/hospital\/doctor\/patients/);
});

test('public booking creates a persistent appointment confirmation', async ({ page }) => {
  await page.goto('/book');
  const available = page.locator('button.front-desk-target').filter({ hasNotText: 'Submit clinic ticket' }).first();
  await expect(available).toBeVisible();
  await page.getByLabel('Patient phone').fill('+2348044444444');
  await page.getByLabel('Chief complaint').fill('Fever and weakness for two days');
  await available.click();
  await page.getByRole('button', { name: 'Submit clinic ticket' }).click();
  await expect(page.getByText('Appointment confirmed')).toBeVisible();
});

test('nurse can force overtake and lock an open schedule slot', async ({ page, request }) => {
  const created = await request.post('http://127.0.0.1:8000/api/v1/tickets', { data: { customer_phone: '+2348033333333', raw_intake_text: 'Routine follow-up for browser test', channel: 'WEB' } });
  expect(created.ok()).toBeTruthy();
  const ticket = await created.json();
  await nurseLogin(page);
  const card = page.locator('article').filter({ hasText: ticket.ticket_number });
  await expect(card).toBeVisible();
  await card.getByRole('button', { name: /FORCED OVERTAKE/ }).click();
  await expect(card.getByText('CRITICAL', { exact: true })).toBeVisible();
  await page.goto('/clinic/appointments');
  let lock = page.getByRole('button', { name: 'Lock slot' }).and(page.locator(':enabled')).first();
  if (await lock.count() === 0) {
    const unlock = page.getByRole('button', { name: 'Unlock slot' }).and(page.locator(':enabled')).first();
    await expect(unlock).toBeVisible();
    await unlock.click();
    lock = page.getByRole('button', { name: 'Lock slot' }).and(page.locator(':enabled')).first();
  }
  await expect(lock).toBeVisible();
  await lock.click();
  await expect(page.getByRole('button', { name: 'Unlock slot' }).first()).toBeVisible();
});
