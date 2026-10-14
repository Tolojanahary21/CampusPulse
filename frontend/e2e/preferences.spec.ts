import { expect, test, type Page } from "@playwright/test";

test.use({ colorScheme: "light" });

function language(page: Page) {
  return page.locator('[data-testid="language-select"]:visible').first();
}

function theme(page: Page) {
  return page.locator('[data-testid="theme-toggle"]:visible').first();
}

async function expectPreferences(
  page: Page,
  locale: string,
  appearance: string,
) {
  await expect(page.locator("html")).toHaveAttribute("lang", locale);
  await expect(page.locator("html")).toHaveAttribute("data-theme", appearance);
  await expect(language(page)).toHaveValue(locale);
}

async function expectNoOverflow(page: Page) {
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 2,
      ),
    )
    .toBe(true);
}

async function signInEnglish(page: Page, email: string) {
  await page.goto("/login");
  await language(page).selectOption("en");
  await page.getByLabel("Email address", { exact: true }).fill(email);
  await page
    .getByLabel("Password", { exact: true })
    .fill("CampusPulse-e2e-2026!");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/app$/);
  await expect(page.locator(".stat-value").first()).not.toHaveText("…");
  await expect(page.locator(".loading")).toHaveCount(0);
  await expect(page.locator(".notice.error")).toHaveCount(0);
}

test("language and appearance persist across public navigation, reload and browser tabs", async ({
  page,
  context,
}) => {
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  await page.goto("/");
  await expectPreferences(page, "fr", "light");
  await language(page).selectOption("en");
  await theme(page).click();
  await expectPreferences(page, "en", "dark");
  await expect(theme(page)).toHaveAccessibleName("Switch to light mode");
  await expect(page).toHaveTitle("Your campus, connected · CampusPulse");

  await page.locator('a[href="/login"]:visible').first().click();
  await expect(page).toHaveURL(/\/login$/);
  await expectPreferences(page, "en", "dark");
  await expect(page).toHaveTitle("Sign in · CampusPulse");
  await expect(
    page.getByRole("heading", { name: "Welcome back.", exact: true }),
  ).toBeVisible();
  await page.locator('a[href="/register"]:visible').first().click();
  await expect(page).toHaveURL(/\/register$/);
  await expectPreferences(page, "en", "dark");
  await expect(page.getByLabel("Your institution")).toBeVisible();
  await expect(
    page.getByLabel("Confirm password", { exact: true }),
  ).toBeVisible();
  await page.reload();
  await expectPreferences(page, "en", "dark");
  await expect(page).toHaveTitle("Create my student account · CampusPulse");
  await expect(page.locator("head title")).toHaveCount(1);
  expect(
    await page.evaluate(() => ({
      locale: localStorage.getItem("campuspulse.locale"),
      theme: localStorage.getItem("campuspulse.theme"),
    })),
  ).toEqual({ locale: "en", theme: "dark" });

  const secondPage = await context.newPage();
  await secondPage.goto("/login");
  await expectPreferences(secondPage, "en", "dark");
  await language(secondPage).selectOption("fr");
  await theme(secondPage).click();
  await expectPreferences(page, "fr", "light");
  await expect(page.getByLabel("Votre établissement")).toBeVisible();
  await expect(page).toHaveTitle("Créer mon compte étudiant · CampusPulse");
  await secondPage.close();
  expect(failures).toEqual([]);
});

test("API login errors translate in both directions without clearing typed values", async ({
  page,
}) => {
  await page.route("**/api/v1/auth/login", (route) =>
    route.fulfill({
      status: 401,
      json: { detail: "Adresse e-mail ou mot de passe incorrect." },
    }),
  );
  await page.goto("/login");
  await language(page).selectOption("en");
  await page.getByLabel("Email address").fill("unknown@campuspulse.test");
  await page.getByLabel("Password", { exact: true }).fill("Incorrect-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator(".notice.error")).toHaveText(
    "Incorrect email address or password.",
  );
  await language(page).selectOption("fr");
  await expect(page.locator(".notice.error")).toHaveText(
    "Adresse e-mail ou mot de passe incorrect.",
  );
  await expect(page.getByLabel("Adresse email")).toHaveValue(
    "unknown@campuspulse.test",
  );
  await expect(page.getByLabel("Mot de passe", { exact: true })).toHaveValue(
    "Incorrect-password",
  );
  await expect(page).toHaveURL(/\/login$/);
});

test("students can use the English library and profile in dark mode on mobile", async ({
  page,
}) => {
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  await signInEnglish(page, "etudiant@campuspulse.test");
  await theme(page).click();
  await page.getByRole("link", { name: "Library", exact: true }).click();
  await expect(page).toHaveURL(/\/app\/documents$/);
  await expect(
    page.getByRole("heading", { name: "Library", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Search documents")).toBeVisible();
  await expect(page.locator(".loading")).toHaveCount(0);
  await expect(page.locator("a.content-card").first()).toBeVisible();
  await page.getByRole("link", { name: "My profile", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "My profile & studies", exact: true }),
  ).toBeVisible();
  const studentName = await page
    .getByLabel("First name", { exact: true })
    .inputValue();
  await expect(
    page.getByRole("heading", { name: "My email preferences" }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Current password", { exact: true }),
  ).toBeVisible();
  await language(page).selectOption("fr");
  await expect(page.getByLabel("Prénom", { exact: true })).toHaveValue(
    studentName,
  );
  await language(page).selectOption("en");
  await expect(page.getByLabel("First name", { exact: true })).toHaveValue(
    studentName,
  );

  await page.setViewportSize({ width: 390, height: 844 });
  await expectPreferences(page, "en", "dark");
  await expectNoOverflow(page);
  await page.getByRole("button", { name: "Open menu", exact: true }).click();
  await expect(page.locator(".sidebar.open")).toBeVisible();
  await page.getByRole("link", { name: "Library", exact: true }).click();
  await expect(page.locator(".sidebar.open")).toHaveCount(0);
  await expect
    .poll(() =>
      page
        .locator(".sidebar")
        .evaluate((element) => element.getBoundingClientRect().right),
    )
    .toBeLessThanOrEqual(0);
  await expect(page.locator(".loading")).toHaveCount(0);
  await expectNoOverflow(page);
  await page.screenshot({
    path: "../.qa/library-mobile-dark-en.png",
    fullPage: true,
  });
  expect(failures).toEqual([]);
});

test("administrators have translated tabs, creation dialogs and role options", async ({
  page,
}) => {
  await signInEnglish(page, "admin@campuspulse.test");
  await page.goto("/app/platform");
  await expect(
    page.getByRole("heading", { name: "Grow CampusPulse" }),
  ).toBeVisible();
  await expect(
    page.getByRole("tab", { name: "Campuses", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await page.getByRole("button", { name: "Add a campus", exact: true }).click();
  const campusDialog = page.getByRole("dialog", {
    name: "Add a campus",
    exact: true,
  });
  await expect(campusDialog).toBeVisible();
  await campusDialog
    .getByLabel("Campus name", { exact: true })
    .fill("Unsaved campus");
  await expect(campusDialog.getByLabel("URL identifier")).toBeVisible();
  await expect(
    campusDialog.getByRole("combobox", { name: "Status", exact: true }),
  ).toContainText("Archived");
  await campusDialog
    .getByRole("button", { name: "Cancel", exact: true })
    .click();
  await expect(campusDialog).toHaveCount(0);
  await page.getByRole("tab", { name: "Accounts", exact: true }).click();
  await expect(
    page.getByRole("columnheader", { name: "Global status" }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Settings", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Platform settings" }),
  ).toBeVisible();
  await expect(page.getByLabel("Support email address")).toBeVisible();

  await page.goto("/app/admin");
  await expect(
    page.getByRole("tab", { name: "Academic structure" }),
  ).toBeVisible();
  await expect(page.getByRole("tab", { name: "Academic years" })).toBeVisible();
  await page.getByRole("tab", { name: "Members", exact: true }).click();
  await page
    .getByRole("button", { name: "Invite a member", exact: true })
    .click();
  const invitation = page.getByRole("dialog", {
    name: "Invite a member",
    exact: true,
  });
  await expect(
    invitation.getByLabel("First name", { exact: true }),
  ).toBeVisible();
  await expect(
    invitation.getByRole("combobox", { name: "Role", exact: true }),
  ).toContainText("Student");
  await expect(
    invitation.getByRole("combobox", { name: "Role", exact: true }),
  ).toContainText("Content publisher");
  await expect(
    invitation.getByRole("combobox", { name: "Role", exact: true }),
  ).toContainText("Campus administrator");
  await invitation.getByRole("button", { name: "Cancel", exact: true }).click();
  await language(page).selectOption("fr");
  await expect(
    page.getByRole("tab", { name: "Membres", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Inviter un membre" }),
  ).toBeVisible();
});

test("public pages fit a 390px screen with English and dark mode", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await language(page).selectOption("en");
  await theme(page).click();
  await expectPreferences(page, "en", "dark");
  await expectNoOverflow(page);
  await page.screenshot({
    path: "../.qa/home-mobile-dark-en.png",
    fullPage: true,
  });
  await page.locator('a[href="/register"]:visible').first().click();
  await expectPreferences(page, "en", "dark");
  await expect(page.getByLabel("Your institution")).toBeVisible();
  await expectNoOverflow(page);
  await page.screenshot({
    path: "../.qa/register-mobile-dark-en.png",
    fullPage: true,
  });
});

test("browser appearance is followed until the user chooses a theme", async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/login");
  await expectPreferences(page, "fr", "dark");
  await page.emulateMedia({ colorScheme: "light" });
  await expectPreferences(page, "fr", "light");
  await theme(page).click();
  await expectPreferences(page, "fr", "dark");
  await page.emulateMedia({ colorScheme: "dark" });
  await page.emulateMedia({ colorScheme: "light" });
  await expectPreferences(page, "fr", "dark");
  await page.reload();
  await expectPreferences(page, "fr", "dark");
});

test("unavailable preference storage does not break language changes or navigation", async ({
  page,
}) => {
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  await page.addInitScript(() => {
    const originalGet = Storage.prototype.getItem;
    const originalSet = Storage.prototype.setItem;
    // Keep the development server's own storage available while reproducing
    // the SecurityError raised when the application's storage is denied.
    Storage.prototype.getItem = function (key: string) {
      if (key.startsWith("campuspulse.")) {
        throw new DOMException("Storage is disabled", "SecurityError");
      }
      return originalGet.call(this, key);
    };
    Storage.prototype.setItem = function (key: string, value: string) {
      if (key.startsWith("campuspulse.")) {
        throw new DOMException("Storage is disabled", "SecurityError");
      }
      return originalSet.call(this, key, value);
    };
  });
  await page.goto("/login");
  await expectPreferences(page, "fr", "light");
  await language(page).selectOption("en");
  await theme(page).click();
  await expectPreferences(page, "en", "dark");
  await page.locator('a[href="/register"]:visible').first().click();
  await expectPreferences(page, "en", "dark");
  await expect(page.getByLabel("Your institution")).toBeVisible();
  await page.reload();
  await expectPreferences(page, "fr", "light");
  await expect(page.getByLabel("Votre établissement")).toBeVisible();
  expect(failures).toEqual([]);
});
