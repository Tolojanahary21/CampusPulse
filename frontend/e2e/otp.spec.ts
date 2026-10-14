import { expect, test } from "@playwright/test";
import { allowTestResend, readVerificationCode } from "./helpers/registration";

test.use({ colorScheme: "light" });

test("verification survives reload, translates, respects cooldown and accepts only the resent code", async ({ page }) => {
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.clock.install();
  await page.goto("/register");
  await page.getByLabel("Prénom", { exact: true }).fill("Verification");
  await page.getByLabel("Nom", { exact: true }).fill("Mobile");
  await page.getByLabel("Votre établissement").selectOption({ index: 1 });
  await page.getByLabel("Adresse email").fill("otp-resume@campuspulse.test");
  await page.locator('input[name="password"]').fill("Verification-e2e-2026!");
  await page.getByLabel("Confirmer le mot de passe").fill("Verification-e2e-2026!");
  const registrationResponse = page.waitForResponse((response) => response.url().endsWith("/auth/register") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Créer mon compte étudiant" }).click();
  const response = await registrationResponse;
  expect(response.status()).toBe(202);
  const challenge = await response.json();
  const originalCode = readVerificationCode(challenge.email);
  await expect(page.getByTestId("otp-code")).toBeVisible();
  await expect(page.getByTestId("otp-code")).toHaveAttribute("autocomplete", "one-time-code");
  await expect(page.getByTestId("resend-code")).toBeDisabled();
  const earlyResend = await page.request.post("http://localhost:8001/api/v1/auth/resend-verification", { data: { challenge_id: challenge.challenge_id } });
  expect(earlyResend.status()).toBe(429);
  expect(Number(earlyResend.headers()["retry-after"])).toBeGreaterThan(0);

  await page.getByTestId("language-select").selectOption("en");
  await page.getByTestId("theme-toggle").click();
  await expect(page.getByRole("heading", { name: "Verify your email address." })).toBeVisible();
  await page.getByTestId("otp-code").fill(originalCode.slice(0, 3));
  await page.reload();
  await expect(page.getByRole("heading", { name: "Verify your email address." })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.getByTestId("otp-code")).toHaveValue("");
  const stored = await page.evaluate(() => JSON.parse(sessionStorage.getItem("campuspulse.registration-verification") ?? "null"));
  expect(stored.challenge_id).toBe(challenge.challenge_id);
  expect(stored.email).toBe(challenge.email);
  expect(Object.keys(stored).sort()).toEqual(["challenge_id", "email", "expires_at", "resend_available_at"].sort());
  expect(JSON.stringify(stored)).not.toContain("Verification-e2e-2026!");
  expect(JSON.stringify(stored)).not.toContain(originalCode);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 2)).toBe(true);
  await page.screenshot({ path: "../.qa/otp-mobile-dark-en.png", fullPage: true });

  allowTestResend(challenge.challenge_id, challenge.email);
  await page.clock.fastForward(Math.max(0, Date.parse(challenge.resend_available_at) - Date.now()) + 2_000);
  await expect(page.getByTestId("resend-code")).toBeEnabled();
  const resentResponse = page.waitForResponse((result) => result.url().endsWith("/auth/resend-verification") && result.request().method() === "POST");
  await page.getByTestId("resend-code").click();
  const resent = await resentResponse;
  expect(resent.status()).toBe(200);
  const replacement = await resent.json();
  const newCode = readVerificationCode(challenge.email);
  expect(replacement).not.toHaveProperty("code");
  expect(JSON.stringify(replacement)).not.toContain(newCode);
  // A new random code can, in principle, equal its predecessor; otherwise the
  // replaced value must be rejected by the actual API before using the new one.
  if (newCode !== originalCode) {
    await page.getByTestId("otp-code").fill(originalCode);
    await page.getByTestId("verify-email").click();
    await expect(page.getByRole("main").getByRole("alert")).toContainText(/code/i);
    await page.getByTestId("language-select").selectOption("fr");
    await expect(page.getByRole("heading", { name: "Vérifiez votre adresse email." })).toBeVisible();
    await expect(page.getByRole("main").getByRole("alert")).toContainText(/code/i);
  }
  await page.getByTestId("language-select").selectOption("en");
  await page.getByTestId("otp-code").fill(newCode);
  await page.getByTestId("verify-email").click();
  await expect(page.getByRole("status")).toContainText("Your student account has been created.");
  expect(await page.evaluate(() => sessionStorage.getItem("campuspulse.registration-verification"))).toBeNull();
  await expect(page.getByRole("link", { name: "Back to sign in" })).toBeVisible();
  expect(failures).toEqual([]);
});

test("an expired pending code still offers resend and changing the registration", async ({ page }) => {
  await page.addInitScript(() => {
    sessionStorage.setItem("campuspulse.registration-verification", JSON.stringify({
      challenge_id: "4460d7cc-0019-4b97-a517-190f2d5c84f4",
      email: "expired-ui@campuspulse.test",
      expires_at: new Date(Date.now() - 10_000).toISOString(),
      resend_available_at: new Date(Date.now() - 20_000).toISOString(),
    }));
  });
  await page.goto("/register");
  await expect(page.getByRole("heading", { name: "Vérifiez votre adresse email." })).toBeVisible();
  await expect(page.getByTestId("verify-email")).toBeDisabled();
  await expect(page.getByTestId("resend-code")).toBeEnabled();
  await page.getByTestId("language-select").selectOption("en");
  await expect(page.getByRole("main")).toContainText(/expired/i);
  await page.getByTestId("change-registration").click();
  await expect(page.getByLabel("Your institution")).toBeVisible();
  await expect(page.getByTestId("otp-code")).toHaveCount(0);
  expect(await page.evaluate(() => sessionStorage.getItem("campuspulse.registration-verification"))).toBeNull();
});
