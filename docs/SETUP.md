# Setup guide – VS Code, Windows, macOS, Linux, GitHub and Codespaces

This guide gets the whole project running on your machine: data, database, analysis, API,
dashboard and Power BI. Follow sections 1–5, then section 6 to run the app.

## 1. What you need

| Tool | Version | Needed for | Required now? |
|---|---|---|---|
| Git | any recent | version control, GitHub | Yes |
| Python | **3.11 or newer** (3.12 or 3.13 recommended) | data, analysis, backend | Yes |
| VS Code | latest | editor | Yes |
| PostgreSQL | 16 (15+ works) | database, SQL analysis, API | Yes |
| Node.js | 22 LTS (20+ works) | React dashboard | Yes, for the dashboard |
| Power BI Desktop | latest | Power BI report | Optional, **Windows only** |

---

## 2. Install the tools

### Windows 10/11

Open **PowerShell** and run the following. `winget` is built into Windows 10/11.

```powershell
winget install --id Git.Git -e
winget install --id Python.Python.3.12 -e
winget install --id Microsoft.VisualStudioCode -e
winget install --id PostgreSQL.PostgreSQL.16 -e      # set and remember the 'postgres' password
winget install --id OpenJS.NodeJS.LTS -e
winget install --id Microsoft.PowerBI -e             # optional
```

Close PowerShell and open a **new** window so PATH updates take effect, then check:

```powershell
git --version; py --version; node --version; psql --version
```

If you install Python from python.org instead, tick **"Add python.exe to PATH"**.

If `psql` is not found, add `C:\Program Files\PostgreSQL\16\bin` to PATH: Start → "Edit the
system environment variables" → Environment Variables → Path → New.

### macOS

Install [Homebrew](https://brew.sh) first, then run:

```bash
brew install git python@3.12 postgresql@16 node@22
brew install --cask visual-studio-code
brew services start postgresql@16
echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:/opt/homebrew/opt/node@22/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Power BI Desktop does not run on macOS. Use the React dashboard, or open the Power BI
specification in `powerbi/` on a Windows machine or VM later.

### Linux (Ubuntu 24.04 / Debian 12)

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip postgresql postgresql-contrib
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt install -y nodejs
sudo snap install code --classic        # or download the .deb from code.visualstudio.com
```

Ubuntu 22.04 ships Python 3.10, which is too old. Install 3.12 from the deadsnakes PPA
(`sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt install python3.12 python3.12-venv`)
and run setup with `PYTHON=python3.12 bash scripts/setup.sh`.

### Windows with WSL (optional)

If you prefer a Linux environment on Windows, install WSL (`wsl --install`), follow the Linux
steps inside it, and open the project with the VS Code **WSL** extension (`code .` from the WSL
terminal). Keep the project inside the WSL filesystem (`~/projects/...`), not under `/mnt/c/`,
or file access will be slow.

---

## 3. Get the project

**From the zip:** extract it to a short path without spaces, such as
`C:\dev\it-service-intelligence` or `~/dev/it-service-intelligence`.

**From GitHub** (once you've pushed it; see section 6):

```bash
git clone https://github.com/<your-username>/it-service-intelligence.git
cd it-service-intelligence
```

---

## 4. Set up in VS Code

1. **File → Open Folder…** and select `it-service-intelligence` (the folder containing `README.md`).
2. If VS Code asks whether you trust the authors, click **Yes, I trust**. Tasks and debugging are
   disabled otherwise.
3. A pop-up offers the **recommended extensions** (from `.vscode/extensions.json`). Click
   **Install All**. If you miss it, open the Extensions view (`Ctrl+Shift+X`), type `@recommended`
   and install them.
4. Open a terminal with **Terminal → New Terminal** and run the one-time setup:

   | Platform | Command |
   |---|---|
   | Windows (PowerShell) | `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1` |
   | macOS / Linux / WSL | `bash scripts/setup.sh` |

   The script:
   - creates a virtual environment in `.venv`
   - installs `requirements.txt`
   - creates `.env` from `.env.example`
   - regenerates the dataset
   - validates it and checks reproducibility
   - runs the tests

   It takes about a minute.

5. Select the interpreter: `Ctrl+Shift+P` (`Cmd+Shift+P` on Mac) → **Python: Select Interpreter**
   → choose the one marked `.venv`. New terminals now activate the environment automatically.

### Daily use in VS Code

| You want to… | Do this |
|---|---|
| Rebuild + validate the data | `Ctrl+Shift+B` (default build task) |
| Run another task | `Ctrl+Shift+P` → **Tasks: Run Task** → choose one (validate only, baseline KPIs, tests) |
| Run / debug tests | Testing panel (flask icon in the left bar) → ▶ |
| Debug the generator or validator | Run and Debug (`Ctrl+Shift+D`) → choose a configuration → F5 |
| Read a CSV | Open it; Rainbow CSV colours the columns. Use **RBQL** for SQL-like queries |
| See the Mermaid diagrams in docs | Open a `.md` file → `Ctrl+Shift+V` (preview) |
| Activate the venv manually | Windows: `.\.venv\Scripts\Activate.ps1` · macOS/Linux: `source .venv/bin/activate` |

### Expected result

The end of the setup output should look like this:

```
Checks: 67  INFO=1  PASS=43  WARN=23
Injected issues detected: 3,213 / 3,219
Structural validation PASSED
OK   tickets.csv                5c5d8f55b121299f...
...
Reproducible: identical output for seed 42
11 passed
```

`WARN` lines are expected. They are the deliberately injected data-quality issues that the
cleaning layer handles later. Only a `FAIL` is a problem.

If the tickets hash differs from `5c5d8f55…`, you are probably on a different numpy or pandas
version. Run `pip install -r requirements.txt` inside the venv; the versions are pinned there.

---

## 5. PostgreSQL setup and database build

First check that you can connect.

```bash
# Windows: run from PowerShell; it asks for the password you set during install
psql -U postgres -h localhost -c "SELECT version();"

# macOS (Homebrew uses your macOS username as the superuser)
psql -d postgres -c "SELECT version();"

# Linux
sudo -u postgres psql -c "SELECT version();"
```

Then edit `.env`, which the setup script created. Choose your own app password; `.env` stays out of Git:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=it_service_intelligence
DB_ADMIN_USER=postgres              # macOS Homebrew: leave blank
DB_ADMIN_PASSWORD=<the password you set when installing PostgreSQL>
DB_APP_USER=itsi_app
DB_APP_PASSWORD=<choose a password>
```

On Linux, the `postgres` superuser has no password by default. Set one once with
`sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'yourpassword';"` and put it in `.env`.

Build the database (about 5 seconds; it ends with 15 PASS checks):

| Platform | Command |
|---|---|
| Windows | `powershell -ExecutionPolicy Bypass -File database\build_database.ps1` |
| macOS / Linux | `bash database/build_database.sh` |
| VS Code | `Ctrl+Shift+P` → **Tasks: Run Task** → **Database: build** |

Then run `python scripts/reconcile_db.py` and `python scripts/run_sql_analysis.py`. Full details
and troubleshooting are in `database/import_instructions.md`.

**SQLTools in VS Code (optional):** open SQLTools in the left bar → **Add New Connection** →
PostgreSQL → enter the values from `.env`. You can then run `.sql` files from the editor.

---

## 6. Run the full application

You need two terminals: one for the API and one for the dashboard. In VS Code, `Ctrl+Shift+P` →
**Tasks: Run Task** → **App: start API + dashboard** starts both at once.

| Step | Windows (PowerShell) | macOS / Linux |
|---|---|---|
| 1. Build the database (once) | `powershell -ExecutionPolicy Bypass -File database\build_database.ps1` | `bash database/build_database.sh` |
| 2. Start the API | `powershell -ExecutionPolicy Bypass -File scripts\start_api.ps1` | `bash scripts/start_api.sh` |
| 3. Start the dashboard | `powershell -ExecutionPolicy Bypass -File scripts\start_dashboard.ps1` | `bash scripts/start_dashboard.sh` |

Then open:
- **Dashboard:** <http://localhost:5173>
- **API documentation (Swagger):** <http://localhost:8000/docs>
- **API health check:** <http://localhost:8000/api/health>, which should show `"database": "ok"`

The first dashboard start runs `npm install`, which takes about a minute. If the dashboard shows
"Cannot reach the API", the API terminal is not running or has stopped with an error. Read its
output; the usual cause is a wrong `DB_APP_PASSWORD` in `.env`.

**Other things to run:**

| What | Command |
|---|---|
| All tests | `python -m pytest tests -q` |
| Regenerate every analysis output | `bash scripts/run_all_analysis.sh` (Windows: `scripts\run_all_analysis.ps1`) |
| Python analysis only | `python analytics/run_analysis.py` → `docs/python_analysis_report.md` |
| Breach-risk model | `python analytics/model.py` → `docs/model_report.md` |
| API latency check | `python scripts/load_test.py` (with the API running) |
| Debug the API | Run and Debug → **API: FastAPI (debug)** → F5 |
| Power BI | Follow `powerbi/README.md` |

## 7. Put it on GitHub

```bash
git init
git add .
git commit -m "Milestone 1: business definition, synthetic dataset and validation"
git branch -M main
```

1. Create an **empty** repository at <https://github.com/new>, called `it-service-intelligence`.
   Don't add a README or .gitignore; the project already has them.
2. Connect and push:

   ```bash
   git remote add origin https://github.com/<your-username>/it-service-intelligence.git
   git push -u origin main
   ```

   With the GitHub CLI you can do both steps at once:
   `gh repo create it-service-intelligence --public --source . --push`

Before pushing, check:

- `git status` must **not** list `.env` or `.venv/`. Both are in `.gitignore`.
- The `.gitattributes` file forces LF line endings. On Windows this stops Git converting the CSVs
  to CRLF, which would change their SHA-256 hashes and fail the reproducibility check.
- Add topics to the repository (About → ⚙): `data-analysis`, `sql`, `postgresql`, `python`,
  `fastapi`, `react`, `power-bi`, `business-analysis`.

---

## 8. GitHub Codespaces (no local install)

Once the project is on GitHub, go to **Code → Codespaces → Create codespace on main**.
`.devcontainer/devcontainer.json` provides Python 3.12, Node 22, PostgreSQL and the VS Code
extensions, and runs `scripts/setup.sh` automatically. Ports 8000 (API) and 5173 (dashboard) are
forwarded automatically. In a codespace, start PostgreSQL with `sudo service postgresql start`, and
set a password for the `postgres` user (section 5) before building the database.

Free personal accounts include a monthly allowance of Codespaces hours. Stop the codespace when
you're not using it.

---

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| `running scripts is disabled on this system` (Windows) | Use the `powershell -ExecutionPolicy Bypass -File …` form shown above, or run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `python` opens the Microsoft Store (Windows) | Settings → Apps → Advanced app settings → App execution aliases → turn off the `python.exe` / `python3.exe` aliases. Use `py` |
| `Python 3.11+ required` | Install Python 3.12; on Linux run setup with `PYTHON=python3.12` |
| `No module named venv` / `ensurepip is not available` (Linux) | `sudo apt install python3-venv` (or `python3.12-venv`) |
| `bash: scripts/setup.sh: Permission denied` | Run it as `bash scripts/setup.sh`, or `chmod +x scripts/*.sh` |
| VS Code doesn't show `.venv` as an interpreter | Run setup first, then `Ctrl+Shift+P` → **Python: Select Interpreter** → **Enter interpreter path** → `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` |
| Tests panel shows "No tests discovered" | Select the `.venv` interpreter, then Testing panel → refresh |
| Reproducibility check shows `DIFF` after cloning on Windows | Line endings were converted. Run `git config core.autocrlf false`, delete the folder and clone again, then rerun setup |
| `psql: command not found` | Add PostgreSQL's `bin` folder to PATH (see section 2) |
| Dashboard says "Cannot reach the API" | Start the API (section 6, step 2) and check <http://localhost:8000/api/health> |
| API returns 503 / health says database unavailable | The database isn't built or `.env` credentials are wrong. Rebuild the database and check `DB_APP_PASSWORD` |
| `npm install` fails | Check `node --version` is 20 or newer; delete `frontend/node_modules` and try again |
| Port 5173 or 8000 already in use | Close the other terminal running it, or set `API_PORT=8001` and update `VITE_API_BASE_URL` in `.env` |
| `pip install` fails behind a company proxy | `pip install --proxy http://user:pass@proxy:port -r requirements.txt`, or ask IT for the proxy and certificate settings |
