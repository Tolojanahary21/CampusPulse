import { test, expect, type Page } from '@playwright/test';

async function login(page: Page, email: string) {
  await page.goto('/login');
  await page.getByLabel('Adresse email').fill(email);
  await page.getByLabel('Mot de passe', { exact: true }).fill('CampusPulse-e2e-2026!');
  await page.getByRole('button', { name: 'Se connecter', exact: true }).click();
  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await expect(page.locator('.stat-value').first()).not.toHaveText('…');
  await expect(page.locator('.loading')).toHaveCount(0);
  await expect(page.locator('.notice.error')).toHaveCount(0);
}

test('student reads an announcement, downloads a private document and participates', async ({ page }) => {
  const failures: string[] = [];
  page.on('pageerror', error => failures.push(error.message));
  await login(page, 'etudiant@campuspulse.test');
  await page.screenshot({ path: '../.qa/student-dashboard.png', fullPage: true });
  await page.goto('/app/announcements');
  await page.locator('a.announcement-row').first().click();
  await expect(page.locator('.content-body')).toBeVisible();
  await page.goto('/app/documents');
  await page.locator('a.content-card').first().click();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: /Télécharger/ }).click();
  expect((await download).suggestedFilename()).toMatch(/\.txt$/);
  await page.goto('/app/community');
  await page.getByRole('button', { name: 'Créer une publication' }).click();
  await page.getByLabel('Titre (facultatif)').fill('Groupe de révision E2E');
  await page.getByLabel('Votre message').fill('Retrouvons-nous à la bibliothèque pour préparer le semestre.');
  await page.getByRole('button', { name: 'Publier', exact: true }).click();
  await expect(page.getByRole('link', { name: 'Groupe de révision E2E' })).toBeVisible();
  await page.getByRole('link', { name: 'Groupe de révision E2E' }).click();
  await expect(page.getByRole('heading', { name: 'Groupe de révision E2E' })).toBeVisible();
  await page.goto('/app/profile');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  expect(failures).toEqual([]);
});

test('campus administrator can create and publish an official announcement', async ({ page }) => {
  await login(page, 'responsable@campuspulse.test');
  await page.goto('/app/announcements');
  await page.getByRole('button', { name: 'Nouvelle annonce' }).click();
  await page.getByLabel('Titre', { exact: true }).fill('Réunion de rentrée E2E');
  await page.getByLabel('Contenu', { exact: true }).fill('La réunion de rentrée se tiendra dans le grand amphithéâtre.');
  await page.getByRole('button', { name: 'Créer le brouillon' }).click();
  await page.getByRole('heading', { name: 'Réunion de rentrée E2E' }).click();
  await page.getByRole('button', { name: 'Publier', exact: true }).click();
  await expect(page.locator('.badge.published').first()).toBeVisible();
  await page.goto('/app/admin');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await page.screenshot({ path: '../.qa/campus-admin.png', fullPage: true });
});

test('platform administrator sees establishments and the mobile menu stays usable', async ({ page }) => {
  await login(page, 'admin@campuspulse.test');
  await page.goto('/app/platform');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await expect(page.getByText('Université d’Antananarivo').last()).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', { name: 'Ouvrir le menu' }).click();
  await expect(page.locator('.sidebar.open')).toBeVisible();
  await page.getByRole('link', { name: 'Bibliothèque', exact: true }).click();
  await expect(page).toHaveURL(/\/app\/documents$/);
  await expect(page.locator('.sidebar.open')).toHaveCount(0);
  await expect(page.locator('.loading')).toHaveCount(0);
  // Wait for the specified 220 ms menu transition to finish before visual capture.
  await page.waitForTimeout(350);
  await page.screenshot({ path: '../.qa/mobile-library.png', fullPage: true });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 2);
  expect(overflow).toBe(false);
});
