# gethired

Give it a list of job posting URLs. For each one it opens the application in a
browser you can see, and Claude fills in the form using your resume and
profile, including a tailored cover letter. You review what was filled in,
fix anything in the browser, and approve the submit.

It's one Python file (`gethired.py`) built on the Anthropic SDK and Playwright.

## Setup

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

export ANTHROPIC_API_KEY=sk-ant-...      # or: ant auth login

cp profile.example.yaml profile.yaml     # fill it in
cp jobs.example.txt jobs.txt             # one job URL per line
cp /path/to/resume.pdf .                 # or point `resume:` at an .html resume
```

`profile.yaml`, `jobs.txt`, PDFs and everything the tool writes are git-ignored.

## Run

```sh
python gethired.py jobs.txt --dry-run    # fill forms, never submit: try this first
python gethired.py jobs.txt
```

For each URL it:

1. Opens the posting. If the form isn't on that page (Lever, Ashby), it
   follows the "Apply" link.
2. Reads every field in the form, including forms inside iframes (Greenhouse
   embeds), with each field's label, type, options and whether it's required.
3. Sends Claude your resume, `profile.yaml`, the job page text and the field
   list. Claude returns an answer for each field, a cover letter, and a
   "needs you" list of required questions it couldn't answer from your info.
4. Fills in the form, uploads your resume and the cover letter as a PDF, and
   saves a screenshot.
5. Prints everything it filled in and waits for you:
   `[s] submit  [m] I'll click submit myself  [k] skip  [q] quit`.
6. After submitting, it asks whether the submission went through, giving you a
   chance to solve a CAPTCHA first, and logs the result.

URLs already marked `submitted` in `applications.jsonl` are skipped on later
runs.

## Output

| Path | What |
|---|---|
| `applications.jsonl` | One record per job: status, company, title, every answer, cover letter |
| `out/<company>-<title>/` | `cover_letter.pdf`, `filled.png`, `after_submit.png` |
| `.browser-profile/` | Browser cookies, so logins carry over between runs |

## Trust boundaries

- **Claude can't act on its own.** Its output only goes into fields that were
  already on the form, and file uploads are limited to your resume and the
  generated cover letter. It can't navigate, click or submit. The tool clicks
  submit only after you press `s`, and pressing Enter is avoided because it
  submits plain forms.
- **Job pages are untrusted input.** The prompt tells Claude to ignore
  instructions embedded in a posting (hidden "AI applicants must..." text is a
  known trick) and to flag them under "needs you".
- **Claude knows only what you give it.** Your resume and `profile.yaml` are
  sent to the Anthropic API with each application. Don't put anything in the
  profile you wouldn't type into a job form (SSN, passwords).

## Model and cost

The model is `claude-opus-5-5` with effort `medium` and structured output, so
answers always match the expected schema. `fallbacks: "default"` is turned on:
if a safety classifier declines a request, the API retries it on Anthropic's
recommended fallback model instead of failing. Your resume and profile are
prompt-cached across jobs.

Rough estimate: $0.10–0.25 per application, depending on how long the job page
is.

## Limits

- **Login-walled sites** (Workday, iCIMS, Taleo) and multi-page wizards aren't
  automated. The browser is visible and keeps cookies, so you can log in and
  finish those by hand.
- **Custom dropdowns** are filled by typing and picking the first suggestion.
  Anything that didn't take is listed as `FIX IN BROWSER`.
- **CAPTCHAs** are left for you to solve during the submit step.
- **LinkedIn Easy Apply and Indeed** aren't supported. Both sites ban
  automation in their terms.

## Tests

```sh
python -m pytest
```

The tests run the full flow (find fields, fill, review, submit, log) against
local Greenhouse- and Lever-style pages, with a stub in place of Claude. If
your Chromium doesn't match Playwright's version, set `CHROMIUM_PATH`.
