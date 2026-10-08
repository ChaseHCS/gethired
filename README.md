# gethired

My job search workspace, built on [career-ops](https://github.com/career-ops-hq/career-ops),
an open-source job search agent that runs in Claude Code (MIT license). This repo
holds only my data and a bit of setup glue. career-ops itself is installed by
`setup.sh` at a pinned commit.

For each job URL, career-ops:
- scores the fit against my CV (1–5) and writes a report
- produces a tailored CV PDF and a cover letter
- tracks the application
- in `apply` mode, reads the live application form through Playwright MCP and
  fills in the drafted answers

It never clicks Submit. I review the form and submit it myself.

## Layout

| Path | What |
|---|---|
| `me/cv.md` | My CV, converted from `windows-portfolio/resume/resume.html`. career-ops uses only this and the profile as facts. |
| `me/config/profile.yml` | Contact details and work authorization (facts from the resume only) |
| `me/data/pipeline.md` | Job URL inbox |
| `me/…` | career-ops adds its own files here as I use it: targeting (`modes/_profile.md`), the tracker (`data/applications.md`), `reports/`, and `output/` (PDFs, git-ignored) |
| `setup.sh` | Installs career-ops at the pinned commit with locked dependencies, registers Playwright MCP, and points career-ops at `me/` |
| `start.sh` | Opens Claude Code in career-ops with access to `me/` |
| `career-ops.package-lock.json` | Lockfile for the pinned release (career-ops doesn't ship one) |

## Setup (once per machine)

Needs git, Node 18.17+ (22.5+ recommended), Claude Code (logged in), and
Google Chrome, which is Playwright MCP's default browser.

```sh
./setup.sh
```

It finishes by running career-ops' `doctor`. Warnings about
`modes/_profile.md` and `portals.yml` are expected until onboarding creates
them.

## Use

```sh
./start.sh
```

1. **First session:** say "set up my profile". career-ops runs onboarding and
   asks about target roles, pay, and location policy. `profile.yml` holds only
   facts from the resume, so nothing there is a guess.
2. **Add jobs:** put URLs under `## Pending` in `me/data/pipeline.md` as
   `- [ ] <url>`, or paste a URL straight into Claude Code.
3. **`/career-ops pipeline`:** evaluates every pending URL. Reports go to
   `me/reports/`, tailored CV PDFs (for scores of 3.0 or higher) to
   `me/output/`, and each job gets a row in the tracker.
4. **`/career-ops apply`** (with the application open): drafts every answer from
   my CV, profile and that job's report, then fills the form in the Playwright
   browser. It lists anything it left for me (some checkboxes, radios and
   uploads, plus any CAPTCHA). I check the form, click Submit, and tell it, and
   it updates the tracker.
5. **`/career-ops tracker`:** shows status. `/career-ops` alone lists every mode.

## Trust and data

- **Pinned code:** the career-ops commit, its npm dependencies (6 packages, none
  with install scripts), and the `@playwright/mcp` version are all pinned.
  career-ops' own postinstall downloads Playwright's Chromium.
- **Untrusted pages:** career-ops treats job postings and form fields as
  untrusted data, never as instructions (see "Untrusted External Content" in
  `career-ops/AGENTS.md`).
- **What leaves the machine:** `me/` content goes to Claude through Claude
  Code. That is billed to my Claude subscription unless `ANTHROPIC_API_KEY` is
  set, which `doctor` warns about.
- **Ashby forms:** Ashby may reject submissions from an automated browser. In
  that case career-ops hands off to my normal browser with a numbered
  copy-paste list.
- **In-app updates:** career-ops offers updates at session start. Prefer
  bumping the pin below, so this repo records what's installed.

## Updating career-ops

Pick a release (`git ls-remote --tags https://github.com/career-ops-hq/career-ops 'career-ops-v*'`),
read its CHANGELOG, set `CAREER_OPS_COMMIT` in `setup.sh` to its commit, then
regenerate the lockfile and rerun setup:

```sh
c=$(sed -n 's/^CAREER_OPS_COMMIT=//p' setup.sh)
git -C career-ops fetch -q --depth 1 https://github.com/career-ops-hq/career-ops.git "$c"
git -C career-ops checkout -q -f --detach FETCH_HEAD
(cd career-ops && rm -f package-lock.json && npm install --package-lock-only --ignore-scripts && cp package-lock.json ../career-ops.package-lock.json)
./setup.sh
```

If `resume.html` in the portfolio changes, update `me/cv.md` to match, or ask
Claude to.
