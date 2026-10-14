import test from "node:test";
import assert from "node:assert/strict";
import { ApiError } from "../src/lib/api.ts";
import { date, label } from "../src/lib/format.ts";
import { errorMessage } from "../src/lib/error-message.ts";

test("roles and statuses use the chosen language while content stays unchanged", () => {
  assert.equal(label("STUDENT"), "Étudiant");
  assert.equal(label("STUDENT", "en"), "Student");
  assert.equal(label("PLATFORM_ADMIN", "en"), "Platform administrator");
  assert.equal(label("SUSPENDED", "fr"), "Suspendu");
  assert.equal(label("SUSPENDED", "en"), "Suspended");
  assert.equal(label("Cours de français", "en"), "Cours de français");
  assert.equal(label(null, "en"), "—");
});

test("dates localize month names and explain missing or invalid values", () => {
  const value = new Date(2026, 0, 14, 12, 30).toISOString();
  assert.match(date(value, false, "fr"), /14 janv\. 2026/);
  assert.match(date(value, false, "en"), /14 Jan 2026/);
  assert.match(date(value, true, "en"), /12:30/);
  assert.equal(date(undefined, false, "en"), "Date not provided");
  assert.equal(date("not-a-date", false, "en"), "Date not provided");
  assert.equal(date("not-a-date", false, "fr"), "Date non renseignée");
});

test("an existing login error can be rendered in either language", () => {
  const original = "Adresse e-mail ou mot de passe incorrect.";
  const error = new ApiError(401, original);
  assert.equal(
    errorMessage(error, "en"),
    "Incorrect email address or password.",
  );
  assert.equal(errorMessage(error, "fr"), original);
  assert.equal(error.message, original);
  assert.equal(
    errorMessage(new Error("Incorrect email address or password."), "fr"),
    original,
  );
});

test("unmapped API errors keep actionable English fallbacks without altering plain content", () => {
  assert.equal(
    errorMessage(new ApiError(413, "Fichier au-delà de la limite."), "en"),
    "This file is too large. Choose a smaller file.",
  );
  assert.equal(
    errorMessage(new ApiError(403, "Accès réservé."), "en"),
    "You do not have permission to perform this action.",
  );
  assert.equal(
    errorMessage(new ApiError(422, "email : valeur invalide"), "en"),
    "Check the entered fields and try again.",
  );
  assert.equal(
    errorMessage(new Error("Un message personnel"), "en"),
    "Un message personnel",
  );
});
