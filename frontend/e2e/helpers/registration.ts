import { spawnSync } from "node:child_process";
import path from "node:path";

/** Read only the disposable Playwright mailbox, never application .env values. */
export function readVerificationCode(recipient: string): string {
  const root = path.resolve("..");
  const python = path.join(
    root,
    "backend",
    ".venv",
    process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
  );
  const result = spawnSync(
    python,
    [
      "-c",
      String.raw`
from pathlib import Path
import re
import sqlite3
import sys

root = Path(sys.argv[1]).resolve()
database = (root / '.qa' / 'e2e.sqlite3').resolve()
if database.parent != (root / '.qa').resolve() or not database.is_relative_to(root):
    raise SystemExit('Unexpected disposable test database path.')
if not database.is_file():
    raise SystemExit('The disposable test database does not exist.')
with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as connection:
    row = connection.execute(
        'SELECT text_body FROM mail_outbox WHERE recipient = ? AND subject = ? ORDER BY created_at DESC LIMIT 1',
        (sys.argv[2], 'Votre code de vérification CampusPulse'),
    ).fetchone()
    code = re.search(r'Code : ([0-9]{6})', row[0]) if row else None
    if not code:
        raise SystemExit('No current verification code in the disposable mailbox.')
    sys.stdout.write(code.group(1))
`,
      root,
      recipient,
    ],
    { encoding: "utf8", windowsHide: true, timeout: 10_000 },
  );
  if (result.status !== 0 || !/^[0-9]{6}$/.test(result.stdout)) {
    // Do not include the mailbox or process output in test diagnostics.
    throw new Error("Could not read the disposable verification mailbox.");
  }
  return result.stdout;
}

/** Advance a single disposable fixture's deadline without waiting a real minute. */
export function allowTestResend(challengeId: string, recipient: string): void {
  const root = path.resolve("..");
  const python = path.join(root, "backend", ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
  const result = spawnSync(python, ["-c", String.raw`
from pathlib import Path
import sqlite3
import sys

root = Path(sys.argv[1]).resolve()
database = (root / '.qa' / 'e2e.sqlite3').resolve()
if database.parent != (root / '.qa').resolve() or not database.is_relative_to(root) or not database.is_file():
    raise SystemExit('Unexpected disposable test database path.')
if sys.argv[3] != 'otp-resume@campuspulse.test':
    raise SystemExit('This helper only updates its named disposable fixture.')
with sqlite3.connect(database.as_uri() + '?mode=rw', uri=True) as connection:
    changed = connection.execute(
        "UPDATE student_registrations SET resend_available_at = datetime('now', '-1 minute') WHERE id = ? AND email = ?",
        (sys.argv[2], sys.argv[3]),
    ).rowcount
    if changed != 1:
        raise SystemExit('The disposable verification fixture was not found.')
`, root, challengeId, recipient], { encoding: "utf8", windowsHide: true, timeout: 10_000 });
  if (result.status !== 0) {
    throw new Error("Could not advance the disposable verification deadline.");
  }
}
