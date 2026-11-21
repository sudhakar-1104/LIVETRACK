# LifeTrack v2.0 — Personal Productivity & Expense Intelligence

**LifeTrack** is a modular, full-stack personal finance and productivity web application built with Django and SQLite. Designed with a responsive dark-mode-enabled vertical sidebar UI, it combines daily task execution, multi-currency expense tracking, monthly budget planning, an isolated physical Cash Wallet, a sandbox What-If Savings Simulator, and executive spending analytics.

---

## ✨ Key Features

* **Command-Center Dashboard (`apps/dashboard`):**
  * At-a-glance KPI cards for Today's Expenses, Month-to-Date (MTD) Net Cash-Flow, Pending/Overdue Tasks, and Task Completion Rate.
  * Overall monthly budget progress gauge and instant Quick-Add Task / Quick-Log Expense forms.
* **Task & Calendar Management (`apps/tasks`):**
  * Priority levels (`High`, `Medium`, `Low`), status tracking, recurring task schedules, and overdue alerts.
  * Interactive monthly calendar grid with a day-inspector sidebar.
* **Multi-Currency Expense & Income Ledger (`apps/finance`):**
  * Log expenses in INR (`₹`) or foreign currencies (`USD`, `EUR`, `GBP`, etc.) with live base-currency conversion previews and customizable exchange rates.
  * Automated recurring bills, custom categories, and payment method management.
* **Monthly Budget Planner (`apps/budgets`):**
  * Overall monthly spending caps and per-category limits with color-coded progress bars and configurable warning thresholds.
* **Standalone Cash Wallet (`apps/cash_wallet`):**
  * Completely isolated physical cash ledger (`CashInflow` & `CashSpend`) to track cash-in-hand and petty cash spends without affecting bank/UPI budgets or dashboard KPIs.
* **Reports & Executive Insights (`apps/reports`):**
  * **Reports & Export:** Daily, Weekly, Monthly, Yearly, and Custom Range financial & productivity reports with Print-ready CSS, `.csv`, and multi-sheet `.xlsx` exports.
  * **Advanced Analytics & Insights:** Automated spending diagnostics, daily cumulative burn-rate curve vs. linear pace, category Month-over-Month variance, top merchants leaderboard, weekday vs. weekend split, and 12-month rolling cash-flow & savings rate trends.
  * **What-If Savings Simulator:** Interactive sandbox pre-loaded with your trailing average income and category spending to test expense cuts and visualize 12-month and 5-year savings projections.
* **Notifications & Backups (`apps/common`, `apps/accounts`):**
  * Deduplicated in-app notification center, persistent Light/Dark mode toggle, and one-click `.sqlite3` database backup downloads.

---

## 🛠️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Backend** | Python 3.12+, Django |
| **Database** | SQLite (`db.sqlite3`) with `Decimal` financial precision |
| **Frontend** | Bootstrap 5.3, Bootstrap Icons, custom `static/css/lifetrack.css` (Light/Dark themes + Print layout) |
| **Charts** | Chart.js 4.4 |
| **Exports** | Native CSV & `openpyxl` (`.xlsx`) |

---

## 📂 Project Structure

```text
lifetrack/
├── apps/
│   ├── accounts/       # Authentication, user preferences (theme/thresholds), SQLite backup download
│   ├── budgets/        # Overall & category monthly budget limits
│   ├── cash_wallet/    # Isolated physical cash-in-hand & cash-spend ledger
│   ├── common/         # In-app notification center & shared utilities
│   ├── dashboard/      # Main command-center overview & quick-entry widgets
│   ├── finance/        # Multi-currency expenses, income, recurring bills, categories & rates
│   ├── reports/        # Period reports, CSV/Excel exports, Insights & What-If Simulator
│   └── tasks/          # To-do lists, recurring tasks & monthly calendar view
├── config/             # Django project settings, root URLs & WSGI entry point
├── static/
│   └── css/
│       └── lifetrack.css
├── templates/          # Responsive vertical-sidebar base layout & module templates
├── tests/              # Automated acceptance & regression test suite
├── .env.example        # Environment variable template
├── manage.py
└── requirements.txt