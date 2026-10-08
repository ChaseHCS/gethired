import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from playwright.sync_api import sync_playwright

import gethired
from gethired import Answer, Application

HERE = Path(__file__).parent

# What the fake Claude answers, keyed by the label gethired extracts for each field.
ANSWERS = {
    "First Name *": ["Chase"],
    "Email *": ["chase@example.com"],
    "Resume/CV *": ["resume"],
    "Cover Letter": ["cover_letter"],
    "Are you legally authorized to work in the US? *": ["Yes"],
    "Will you now or in the future require visa sponsorship?": ["No"],
    "Which areas interest you?": ["Red team", "AppSec"],
    "I agree to the privacy policy": ["I agree to the privacy policy"],
    "Location (City)": ["Boston"],
}


class FakeClaude:
    """Stands in for anthropic.Anthropic(): answers by field label and records each request."""

    def __init__(self):
        self.requests = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self.parse))

    def parse(self, **kwargs):
        self.requests.append(kwargs)
        prompt = kwargs["messages"][0]["content"][-1]["text"]
        fields = json.loads(prompt.split("Application form fields:\n", 1)[1])
        app = Application(
            company="Example Corp",
            job_title="Security Engineer",
            answers=[Answer(field_id=f["id"], values=ANSWERS.get(f["label"], [])) for f in fields],
            cover_letter="Dear Example Corp,\nI break things.",
            needs_you=[],
        )
        return SimpleNamespace(stop_reason="end_turn", stop_details=None, parsed_output=app)


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        # CHROMIUM_PATH lets you point at a Chromium that doesn't match Playwright's bundled revision.
        browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH"))
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    page = browser.new_page()
    yield page
    page.close()


@pytest.fixture
def workdir(tmp_path, monkeypatch, browser):
    monkeypatch.chdir(tmp_path)
    gethired.OUT.mkdir()
    return gethired.html_to_pdf(browser, "<h1>Chase Hanson</h1>", tmp_path / "resume.pdf")


def run(page, browser, resume, monkeypatch, replies, dry_run=False):
    replies = iter(replies)
    monkeypatch.setattr("builtins.input", lambda _: next(replies))
    claude = FakeClaude()
    url = (HERE / "job.html").as_uri()
    gethired.apply_to(page, browser, claude, url, "name: Chase", resume, dry_run)
    return claude


def test_extracts_fields_from_embedded_form(page):
    _, fields, _ = gethired.open_form(page, (HERE / "job.html").as_uri())
    got = {f["label"]: (f["kind"], f.get("options")) for f in fields}
    assert got == {
        "First Name *": ("text", None),
        "Email *": ("text", None),
        "Phone": ("text", None),
        "Resume/CV *": ("file", None),
        "Cover Letter": ("textarea", None),
        "Are you legally authorized to work in the US? *": ("select", ["Yes", "No"]),
        "Will you now or in the future require visa sponsorship?": ("radio", ["Yes", "No"]),
        "Which areas interest you?": ("checkbox", ["Red team", "AppSec", "GRC"]),
        "I agree to the privacy policy": ("checkbox", ["I agree to the privacy policy"]),
        "Location (City)": ("combobox", None),
    }
    required = {f["label"] for f in fields if f["required"]}
    assert required == {"First Name *", "Email *", "Resume/CV *", "Are you legally authorized to work in the US? *"}


def test_follows_apply_link_without_clicking_submit(page):
    _, fields, _ = gethired.open_form(page, (HERE / "lever.html").as_uri())
    assert page.url.endswith("/form.html")
    assert len(fields) == 10


def test_fills_form_and_submits_after_approval(page, browser, workdir, monkeypatch):
    claude = run(page, browser, workdir, monkeypatch, replies=["s", "y"])

    form = page.frames[1]
    assert form.input_value("#first_name") == "Chase"
    assert form.input_value("#email") == "chase@example.com"
    assert form.input_value("#cover") == "Dear Example Corp,\nI break things."
    assert form.input_value("#auth") == "1"
    assert form.is_checked("input[name=sponsor][value=n]")
    assert [form.is_checked(f"input[name=areas][value={v}]") for v in "abc"] == [True, True, False]
    assert form.is_checked("#consent")
    assert form.get_attribute("#loc", "data-picked") == "Boston, MA"
    assert form.eval_on_selector("#resume", "e => e.files[0].name") == "resume.pdf"
    assert form.get_attribute("body", "data-submitted") == "yes"

    record = json.loads(Path("applications.jsonl").read_text())
    assert record["status"] == "submitted"
    assert record["answers"]["First Name *"] == ["Chase"]
    assert Path("out/example-corp-security-engineer/cover_letter.pdf").exists()
    assert Path("out/example-corp-security-engineer/filled.png").exists()

    request = claude.requests[0]
    assert request["model"] == "claude-opus-5-5"
    assert request["fallbacks"] == "default"
    assert request["output_format"] is Application
    assert request["messages"][0]["content"][0]["source"]["media_type"] == "application/pdf"
    assert gethired.already_submitted() == {(HERE / "job.html").as_uri()}


def test_dry_run_never_submits(page, browser, workdir, monkeypatch):
    run(page, browser, workdir, monkeypatch, replies=[""], dry_run=True)

    form = page.frames[1]
    assert form.input_value("#first_name") == "Chase"
    assert form.get_attribute("body", "data-submitted") is None
    assert json.loads(Path("applications.jsonl").read_text())["status"] == "dry-run"


def test_skip_does_not_submit(page, browser, workdir, monkeypatch):
    run(page, browser, workdir, monkeypatch, replies=["k"])

    assert page.frames[1].get_attribute("body", "data-submitted") is None
    assert json.loads(Path("applications.jsonl").read_text())["status"] == "skipped"
