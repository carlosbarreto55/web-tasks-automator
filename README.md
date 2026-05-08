# web-task-automation-engine
======


A Python + Selenium CLI tool that automates website interactions through a config-driven pipeline: login, navigate, scrape, and optionally solve lab assignments with AI.

## Features

- **Headless login** — authenticate against any site with CSS-selector-based form filling and success/failure detection
- **Post-login navigation** — execute multi-step sequences (clicks, URL navigations, configurable waits)
- **Data scraping** — extract page content via CSS selectors (single values or multi-element flat lists)
- **Lab assignment scraping** — discover and click the latest assignment link, scrape the full page body
- **AI-powered solving** — send scraped lab content to an AI provider (OpenCode, OpenAI, or Ollama) and save generated solution files
- **Telegram notifications** — send scraped lab statements and AI-generated solutions to a Telegram chat via bot
- **Session reuse** — save and restore cookies to skip login on subsequent runs
- **Multi-site batch processing** — process multiple sites in a single invocation, with per-site JSON output
- **Retry logic** — classifies errors as client (fail fast) or network (retry up to 3x with fresh browser), so transient issues don't kill the run

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.10+ |
| Browser automation | Selenium 4.15+ |
| Driver management | webdriver-manager 4.0+ |
| HTTP client | httpx 0.27+ |
| AI APIs | OpenAI-compatible + Ollama |
| Testing | pytest 8.0+ |

## Installation

```bash
git clone <repo-url>
cd login-automator
pip install -r requirements.txt
```

Chrome/Chromium must be installed and discoverable on `$PATH` or at `~/chromium/`. The chromedriver binary is auto-downloaded by `webdriver-manager` if not found locally.

## Configuration

### Environment variables (`.env`)

Create a `.env` file in the project root:

```ini
OPENCODE_API_KEY=sk-...      # or OPENAI_API_KEY — required for AI solving
```

### Site configuration (`config/sites.json`)

Copy the schema template and fill in your site details:

```bash
cp config/sites.example.json config/sites.json
```

`config/sites.json` contains credentials and is gitignored. See `config/sites.example.json` for the full schema. Required fields per site:

- `name`, `url`, `credentials.{username, password}`
- `selectors.{username_input, password_input, submit_button, success_indicator, failure_indicator}`

Optional blocks:
- `navigate` — array of `{click, url, wait_for, wait_after}` steps
- `scrape` — `target_url` + `data_selectors` map (string = single, list = multi)
- `labs` — `lab_link_selector`, `locator_type` (`css` or `xpath`), `output_file`
- `labs.ai` — `provider` (`opencode`/`openai`/`ollama`), `model`, `output_dir`

### Telegram configuration (`config/telegram.json`)

Copy the template and fill in your bot credentials:

```bash
cp config/telegram.example.json config/telegram.json
```

Fields:
- `enabled` — must be `true` for notifications to fire
- `bot_token` — your Telegram bot token (obtained from [@BotFather](https://t.me/BotFather))
- `chat_id` — the target chat ID (your user ID or group ID)

`config/telegram.json` contains the bot token and is gitignored.

## How to Use

### Quick start — full pipeline

```bash
python login_automator.py --solve --notify
```

This single command:
1. Opens a headless Chrome browser
2. Logs into the target site using the credentials in `config/sites.json`
3. Navigates through the post-login steps (clicks, waits) defined in the config
4. Finds and clicks the last lab/assignment link
5. Scrapes the full lab content and saves it to a file
6. Sends the lab statement to your Telegram chat
7. Feeds each lab question to the AI provider and saves the generated solution files
8. Sends the solutions to your Telegram chat

### Step by step

1. **Install dependencies**

   ```bash
   git clone <repo-url>
   cd login-automator
   pip install -r requirements.txt
   ```

2. **Configure the target site**

   ```bash
   cp config/sites.example.json config/sites.json
   # Edit config/sites.json with your credentials and navigation steps
   ```

   Required per site: `name`, `url`, `credentials.{username, password}`, and all 5 `selectors.*` fields. Add optional `navigate`, `scrape`, and `labs` blocks to control post-login behavior.

3. **Set up AI solving (optional)**

   Create a `.env` file:
   ```ini
   OPENCODE_API_KEY=sk-...
   ```

   Supported providers (configured in `sites.json` under `labs.ai`): `opencode`, `openai`, `ollama`.

4. **Set up Telegram notifications (optional)**

   ```bash
   cp config/telegram.example.json config/telegram.json
   # Edit config/telegram.json with your bot_token and chat_id
   ```

   Create a bot via [@BotFather](https://t.me/BotFather) on Telegram and get your chat ID.

5. **Run**

   ```bash
   # Full run: login → scrape → AI-solve → Telegram notify
   python login_automator.py --solve --notify

   # Skip login on subsequent runs (reuse saved session)
   python login_automator.py --scrape-only --cookies-file cookies.json --solve --notify
   ```

### CLI Reference

```bash
python login_automator.py [OPTIONS]
```

| Flag | Purpose |
|------|---------|
| `--config PATH` | Path to config JSON (default: `config/sites.json`) |
| `--site NAME` | Process only one named site |
| `--no-verbose` | Suppress debug output to stderr |
| `--scrape-only` | Skip login; reuse existing session cookies |
| `--solve` | Send scraped lab content to AI and save solution files |
| `--notify` | Send results to Telegram |
| `--cookies-file PATH` | Load cookies JSON (required with `--scrape-only`) |
| `--save-cookies PATH` | Save session cookies after successful login |
| `--report-file PATH` | Append human-readable report to a file |
| `--telegram-config PATH` | Path to Telegram config (default: `config/telegram.json`) |

### Examples

```bash
# Login to all configured sites, scrape data, print JSON to stdout
python login_automator.py

# Process a single site with verbose debug output suppressed
python login_automator.py --site my-portal --no-verbose

# Reuse a saved session to scrape labs and generate AI solutions
python login_automator.py --scrape-only --cookies-file cookies.json --solve

# Full pipeline: login, solve with AI, send to Telegram, save cookies
python login_automator.py --solve --notify --save-cookies cookies.json

# Login, save cookies for later reuse, and write a report
python login_automator.py --save-cookies cookies.json --report-file report.txt
```

### Output

- **stdout**: Machine-readable JSON, one object per site per line. Pipe-friendly.
- **stderr**: Debug output (suppress with `--no-verbose`).
- **Exit codes**: `0` = all sites succeeded, `1` = any failure.

## Project Structure

```
login_automator.py              # CLI entry point, orchestration, retry loop
src/
  config/config.py              # Config loading + schema validation
  login/
    driver.py                   # Headless Chrome driver factory
    login.py                    # Login flow + cookie persistence
    classifier.py               # Error classification (client vs network)
  scraping/
    scraper.py                  # CSS selector data extraction
    navigator.py                # Multi-step post-login navigation
    lab_finder.py               # Lab link detection + interaction
  ai/
    ai_client.py                # OpenAI-compatible + Ollama API clients
    solver.py                   # AI-powered lab question solver
  notifications/
    notifier.py                 # Notification orchestration (Telegram)
    telegram.py                 # Telegram Bot API client
  reporter.py                   # Human-readable report formatter
config/
  sites.example.json            # Canonical config schema
  sites.json                    # Real config (gitignored)
tests/                          # Unit tests (mocked)
it/                             # Integration tests (real browser)
output/
  solutions/                    # AI-generated solution files
```

## Testing

```bash
# Unit tests (mocked, no browser needed)
pytest tests/

# Integration tests (requires Chrome)
pytest -m "integration" it/

# All tests
pytest tests/ it/
```

Integration tests use public sites (`the-internet.herokuapp.com`, `books.toscrape.com`) — no real credentials needed.

## Security

- `config/sites.json` is gitignored and never committed
- Credential values never appear in stdout, stderr, or reports
- API keys are loaded from `.env` via `python-dotenv`

## Why this project matters

This project explores:
- Automating real-world workflows across web platforms
- Integrating LLMs into automation pipelines
- Designing resilient automation systems with retry logic and state persistence

## Disclaimer

This project is intended for studying automation assist, scraping, and AI workflows.
It is not intended for academic dishonesty or misuse.

=======
## License

MIT
