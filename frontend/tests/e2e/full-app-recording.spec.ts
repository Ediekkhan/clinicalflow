import { expect, test, type Page, type Response } from '@playwright/test';

test.setTimeout(10 * 60_000);

const publicRoutes = [
  '/', '/hospitals', '/specialists', '/pricing', '/blog', '/book', '/book-demo',
  '/signup', '/signup/patient', '/signup/specialist', '/signup/hospital', '/signup/clinic',
  '/signup/nurse', '/signup/pharmacy', '/signup/laboratory', '/signup/hmo',
  '/signup/government', '/signup/platform-admin', '/privacy', '/terms',
];

const patientRoutes = ['/dashboard', '/dashboard/chat', '/dashboard/queue', '/dashboard/appointments', '/dashboard/card', '/dashboard/history', '/dashboard/settings', '/my-visit', '/my-card'];
const specialistRoutes = ['/specialist/dashboard', '/specialist/appointments', '/specialist/patients', '/specialist/referrals', '/specialist/schedule', '/specialist/notes', '/specialist/messages', '/specialist/earnings', '/specialist/notifications', '/specialist/settings'];
const hospitalRoutes = ['/hospital/dashboard', '/hospital/queue', '/hospital/doctor/patients', '/hospital/specialists', '/hospital/appointments', '/hospital/departments', '/hospital/schedule', '/hospital/waiting-room', '/hospital/analytics', '/hospital/notifications', '/hospital/settings'];
const nurseAndClinicRoutes = ['/nurse/dashboard', '/nurse/queue', '/nurse/patients', '/nurse/vitals', '/nurse/visits', '/nurse/care-plans', '/nurse/schedule', '/nurse/notifications', '/nurse/settings', '/clinic/dashboard', '/clinic/queue', '/clinic/appointments', '/clinic/doctors', '/clinic/analytics', '/clinic/notifications', '/clinic/settings'];
const administratorRoutes = ['/dashboard/admin', '/dashboard/admin/users', '/dashboard/admin/hospitals', '/dashboard/admin/audit-log', '/dashboard/admin/system-health', '/dashboard/admin/settings'];
const pharmacyRoutes = ['/pharmacy/dashboard', '/pharmacy/prescriptions', '/pharmacy/inventory', '/pharmacy/dispensed-log', '/pharmacy/deliveries', '/pharmacy/patients', '/pharmacy/analytics', '/pharmacy/notifications', '/pharmacy/settings'];
const laboratoryRoutes = ['/lab/dashboard', '/lab/requests', '/lab/worklist', '/lab/collections', '/lab/specimens', '/lab/results', '/lab/critical-results', '/lab/equipment', '/lab/patients', '/lab/analytics', '/lab/notifications', '/lab/settings'];
const hmoRoutes = ['/hmo/dashboard', '/hmo/members', '/hmo/enrollees', '/hmo/authorizations', '/hmo/claims', '/hmo/payments', '/hmo/facilities', '/hmo/utilization', '/hmo/analytics', '/hmo/notifications', '/hmo/settings'];
const governmentRoutes = ['/moh/dashboard', '/moh/hospitals', '/moh/reports', '/moh/surveillance', '/moh/settings'];

async function visitRoutes(page: Page, routes: string[], failures: string[]) {
  for (const route of routes) {
    await test.step(`Open ${route}`, async () => {
      const errors: string[] = [];
      const onPageError = (error: Error) => errors.push(error.message);
      const onResponse = (response: Response) => {
        if (response.status() >= 500) errors.push(`${response.status()} ${response.url()}`);
      };
      page.on('pageerror', onPageError);
      page.on('response', onResponse);
      try {
        const response = await page.goto(route, { waitUntil: 'domcontentloaded' });
        if (response && response.status() >= 400) errors.push(`${response.status()} ${route}`);
        await page.waitForTimeout(180);
        const path = new URL(page.url()).pathname;
        if (/\/(auth\/login|hospital\/login|specialist\/login|login)$/.test(path)) errors.push(`unexpected authentication redirect to ${page.url()}`);
        if (await page.getByText(/Runtime TypeError|Console Error|Application error/i).count()) errors.push('visible runtime error overlay');
      } catch (error) {
        errors.push(error instanceof Error ? error.message : String(error));
      } finally {
        page.off('pageerror', onPageError);
        page.off('response', onResponse);
      }
      failures.push(...errors.map((error) => `${route}: ${error}`));
    });
  }
}

async function patientLogin(page: Page) {
  await page.goto('/login');
  await page.getByLabel('Phone number').fill('+2348012345678');
  await page.getByLabel('Password').fill('Password123!');
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

async function specialistLogin(page: Page) {
  await page.goto('/specialist/login');
  await page.getByLabel('Email address').fill('dr.ada@example.com');
  await page.getByLabel('Password').fill('Password123!');
  await page.getByRole('button', { name: 'Sign In' }).click();
  await expect(page).toHaveURL(/\/specialist\/dashboard/);
}

async function hospitalLogin(page: Page, admin = false) {
  await page.goto('/hospital/login');
  if (admin) await page.getByRole('button', { name: 'Hospital Admin' }).click();
  await page.getByLabel('Work email').fill(admin ? 'admin.grace@example.com' : 'doctor.bassey@example.com');
  await page.getByLabel('Hospital password').fill('Password123!');
  await page.getByRole('button', { name: 'Enter Hospital Workspace' }).click();
  await expect(page).toHaveURL(admin ? /\/hospital\/dashboard/ : /\/hospital\/doctor\/patients/);
}

async function sectorLogin(page: Page, role: 'pharmacy' | 'laboratory' | 'hmo' | 'government', email: string) {
  const response = await page.request.post(`http://127.0.0.1:8100/api/v1/auth/${role}/login`, { data: { email, password: 'Password123!' } });
  expect(response.ok(), await response.text()).toBeTruthy();
}

async function pinLogin(page: Page, role: 'nurse' | 'admin') {
  await page.goto('/auth/login');
  if (role === 'admin') await page.getByRole('button', { name: 'System Administrator' }).click();
  for (const digit of role === 'admin' ? ['1', '3', '5', '7'] : ['2', '4', '6', '8']) await page.getByRole('button', { name: digit, exact: true }).click();
  await page.getByRole('button', { name: 'Login' }).click();
  await expect(page).toHaveURL(role === 'admin' ? /\/dashboard\/admin/ : /\/nurse\/queue/);
}

test('record all public pages and authenticated healthcare workspaces', async ({ page }) => {
  const failures: string[] = [];
  await visitRoutes(page, publicRoutes, failures);
  await patientLogin(page); await visitRoutes(page, patientRoutes, failures);
  await page.context().clearCookies(); await specialistLogin(page); await visitRoutes(page, specialistRoutes, failures);
  await page.context().clearCookies(); await hospitalLogin(page); await visitRoutes(page, hospitalRoutes, failures);
  await page.context().clearCookies(); await hospitalLogin(page, true); await visitRoutes(page, ['/hospital/admin/settings'], failures);
  await page.context().clearCookies(); await pinLogin(page, 'nurse'); await visitRoutes(page, nurseAndClinicRoutes, failures);
  await page.context().clearCookies(); await pinLogin(page, 'admin'); await visitRoutes(page, administratorRoutes, failures);
  await page.context().clearCookies(); await sectorLogin(page, 'pharmacy', 'pharmacy@example.com'); await visitRoutes(page, pharmacyRoutes, failures);
  await page.context().clearCookies(); await sectorLogin(page, 'laboratory', 'laboratory@example.com'); await visitRoutes(page, laboratoryRoutes, failures);
  await page.context().clearCookies(); await sectorLogin(page, 'hmo', 'hmo@example.com'); await visitRoutes(page, hmoRoutes, failures);
  await page.context().clearCookies(); await sectorLogin(page, 'government', 'government@example.com'); await visitRoutes(page, governmentRoutes, failures);
  expect(failures, failures.join('\n')).toEqual([]);
});
