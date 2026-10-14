import { expect, test } from "@playwright/test";
import { readVerificationCode } from "./helpers/registration";

test("a student verifies an email code before signing in and cannot administer accounts", async ({
  page,
}) => {
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page
    .locator(".landing-intro")
    .getByRole("link", { name: "Créer mon compte étudiant", exact: true })
    .click();
  await expect(page).toHaveURL(/\/register$/);
  await expect(page.getByRole("heading", { level: 1 }).last()).toHaveText(
    "Votre vie étudiante commence ici.",
  );
  await page.getByLabel("Prénom", { exact: true }).fill("Nouvel");
  await page.getByLabel("Nom", { exact: true }).fill("Étudiant");
  await page.getByLabel("Votre établissement").selectOption({ index: 1 });
  await page.getByLabel("Adresse email").fill("inscription@campuspulse.test");
  await page.locator('input[name="password"]').fill("Inscription-e2e-2026!");
  await page.getByLabel("Confirmer le mot de passe").fill("Autre-mot-de-passe");
  await page.screenshot({ path: "../.qa/register-mobile.png", fullPage: true });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth + 2,
    ),
  ).toBe(false);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({
    path: "../.qa/register-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });

  let registrationRequests = 0;
  page.on("request", (request) => {
    if (
      request.method() === "POST" &&
      request.url().endsWith("/auth/register")
    ) {
      registrationRequests += 1;
      expect(request.postDataJSON()).not.toHaveProperty("role");
    }
  });
  await page.getByRole("button", { name: "Créer mon compte étudiant" }).click();
  await expect(page.getByRole("main").getByRole("alert")).toHaveText(
    "Les mots de passe ne correspondent pas.",
  );
  expect(registrationRequests).toBe(0);
  await page
    .getByLabel("Confirmer le mot de passe")
    .fill("Inscription-e2e-2026!");
  const registrationResponse = page.waitForResponse(
    (response) => response.request().method() === "POST" && response.url().endsWith("/auth/register"),
  );
  await page.getByRole("button", { name: "Créer mon compte étudiant" }).click();
  const registration = await registrationResponse;
  expect(registration.status()).toBe(202);
  const challenge = await registration.json();
  expect(challenge.verification_required).toBe(true);
  expect(challenge.email).toBe("inscription@campuspulse.test");
  expect(challenge).not.toHaveProperty("code");
  expect(challenge).not.toHaveProperty("otp");
  expect(challenge).not.toHaveProperty("password");
  await expect(page.getByRole("heading", { name: "Vérifiez votre adresse email." })).toBeVisible();
  await expect(page.getByTestId("resend-code")).toBeDisabled();
  expect(registrationRequests).toBe(1);
  const beforeVerification = await page.request.post("http://localhost:8001/api/v1/auth/login", {
    data: { email: challenge.email, password: "Inscription-e2e-2026!" },
  });
  expect(beforeVerification.status()).toBe(401);
  const code = readVerificationCode(challenge.email);
  expect(JSON.stringify(challenge)).not.toContain(code);
  await page.getByTestId("otp-code").fill(code === "000000" ? "111111" : "000000");
  await page.getByTestId("verify-email").click();
  await expect(page.getByRole("main").getByRole("alert")).toBeVisible();
  await expect(page.getByTestId("otp-code")).toBeVisible();
  await page.getByTestId("otp-code").fill(code);
  const verificationResponse = page.waitForResponse(
    (response) => response.url().endsWith("/auth/verify-email"),
  );
  await page.getByTestId("verify-email").click();
  expect((await verificationResponse).status()).toBe(201);
  await expect(page.getByRole("status")).toContainText(
    "Votre compte étudiant a été créé.",
  );
  expect(await page.evaluate(() => sessionStorage.getItem("campuspulse.registration-verification"))).toBeNull();
  await expect(page).toHaveURL(/\/register$/);
  await page.getByRole("link", { name: "Retour à la connexion" }).click();
  await page.getByLabel("Adresse email").fill("inscription@campuspulse.test");
  await page
    .getByLabel("Mot de passe", { exact: true })
    .fill("Inscription-e2e-2026!");
  await page.getByRole("button", { name: "Se connecter", exact: true }).click();
  await expect(page).toHaveURL(/\/app$/);
  await expect(page.locator(".stat-value").first()).not.toHaveText("…");
  await expect(page.locator(".notice.error")).toHaveCount(0);

  const me = await page.request.get("http://localhost:8001/api/v1/auth/me");
  expect(me.status()).toBe(200);
  const user = await me.json();
  expect(user.roles.map((role: { role: string }) => role.role)).toEqual([
    "STUDENT",
  ]);
  expect(user.campuses).toHaveLength(1);
  const forbidden = await page.request.get(
    "http://localhost:8001/api/v1/platform/users",
  );
  expect(forbidden.status()).toBe(403);
  await page.goto("/app/platform");
  await expect(
    page.getByRole("heading", {
      name: "Cet espace est réservé à la plateforme",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Inviter|Créer un compte/ }),
  ).toHaveCount(0);
  await page.goto("/app/admin");
  await expect(
    page.getByRole("heading", {
      name: "Cet espace est réservé à l’administration",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Plateforme", exact: true }),
  ).toHaveCount(0);
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth + 2,
  );
  expect(overflow).toBe(false);
  expect(failures).toEqual([]);
});

test("the login page links to student registration", async ({ page }) => {
  await page.goto("/login");
  await page
    .getByRole("link", { name: "Créer mon compte étudiant", exact: true })
    .click();
  await expect(page).toHaveURL(/\/register$/);
  await expect(page.getByLabel("Votre établissement")).toBeVisible();
  await expect(
    page.getByText(
      "Les comptes des responsables sont créés sur invitation par l’administration.",
    ),
  ).toBeVisible();
  await expect(page.getByLabel("Rôle", { exact: true })).toHaveCount(0);
});

test("closed registrations explain why no form is available", async ({
  page,
}) => {
  await page.route("**/api/v1/auth/registration-options", (route) =>
    route.fulfill({
      json: { enabled: false, campuses: [] },
    }),
  );
  await page.goto("/register");
  await expect(page.getByRole("status")).toContainText(
    "Les inscriptions étudiantes sont temporairement fermées.",
  );
  await expect(
    page.getByRole("button", { name: "Créer mon compte étudiant" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: "Se connecter", exact: true }),
  ).toBeVisible();
});

test("registration without an active campus gives a useful empty state", async ({
  page,
}) => {
  await page.route("**/api/v1/auth/registration-options", (route) =>
    route.fulfill({
      json: { enabled: true, campuses: [] },
    }),
  );
  await page.goto("/register");
  await expect(page.getByRole("status")).toContainText(
    "Aucun établissement n’est ouvert aux inscriptions pour le moment.",
  );
  await expect(
    page.getByRole("button", { name: "Créer mon compte étudiant" }),
  ).toHaveCount(0);
});

test("registration options can be retried after a server error", async ({
  page,
}) => {
  const unavailable = async (route: import("@playwright/test").Route) =>
    route.fulfill({
      status: 503,
      json: { detail: "Les établissements sont temporairement indisponibles." },
    });
  await page.route("**/api/v1/auth/registration-options", unavailable);
  await page.goto("/register");
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "Les établissements sont temporairement indisponibles.",
  );
  await page.unroute("**/api/v1/auth/registration-options", unavailable);
  await page.getByRole("button", { name: "Réessayer" }).click();
  await expect(page.getByLabel("Votre établissement")).toBeVisible();
  await expect(page.getByRole("main").getByRole("alert")).toHaveCount(0);
});
