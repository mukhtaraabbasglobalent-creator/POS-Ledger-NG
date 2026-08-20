# User Guide

# POS Ledger NG

## Introduction

Welcome to POS Ledger NG.

POS Ledger NG is an offline-first financial management platform built for POS agents, mobile money operators, and small businesses. It helps users record transactions, monitor cash flow, calculate service charges automatically, and generate financial reports.

---

# System Requirements

To run POS Ledger NG, ensure you have:

- Python 3.10 or later
- SQLite (included with Python)
- Git (optional)
- Windows, Linux, or macOS

---

# Installation

## Step 1

Clone the repository.

```bash
git clone https://github.com/mukhtaraabbasglobalent-creator/POS-Ledger-NG.git
```

---

## Step 2

Navigate into the project directory.

```bash
cd POS-Ledger-NG
```

---

## Step 3

Install the required packages.

```bash
pip install -r requirements.txt
```

---

## Step 4

Start the application.

```bash
python gui_app.py
```

---

# Using POS Ledger NG

## Recording a Transaction

Open the application and enter:

- Transaction type
- Amount
- Date
- Time

The application automatically calculates the applicable service charge.

Save the transaction to store it in the local database.

---

## Viewing Reports

Users can generate:

- Daily reports
- Monthly reports
- Financial summaries

Reports display:

- Total deposits
- Total withdrawals
- Charges earned
- Profit
- Cash position

---

## Exporting Reports

Reports can be exported as CSV files for:

- Business analysis
- Auditing
- Tax preparation
- Record keeping

---

# Charge Calculation

The system automatically calculates service charges according to configured pricing rules.

Example:

| Transaction Amount | Charge |
|--------------------|---------|
| ₦1,000–₦9,999 | ₦100 |
| ₦10,000–₦19,999 | ₦200 |

Additional pricing rules can be configured as the product evolves.

---

# Database

The application stores data locally using SQLite.

Database file:

```
pos_agent.db
```

---

# Best Practices

To keep records safe:

- Back up exported reports regularly.
- Verify transaction details before saving.
- Keep Python updated.
- Store the database securely.

---

# Troubleshooting

## Application Does Not Start

Ensure Python is installed correctly.

Run:

```bash
python --version
```

---

## Missing Packages

Install dependencies again.

```bash
pip install -r requirements.txt
```

---

## Database Errors

If the database file becomes corrupted, restore it from a backup or create a new database.

---

# Planned Improvements

Future releases are planned to include:

- Android application
- Cloud synchronization
- User accounts
- PIN authentication
- Database encryption
- AI-powered insights
- PDF reports
- Multi-user support

---

# Support

If you experience issues or have suggestions:

- Open an issue on the GitHub repository.
- Review the documentation in this repository.

GitHub Repository:

https://github.com/mukhtaraabbasglobalent-creator/POS-Ledger-NG

---

# License

POS Ledger NG is licensed under the MIT License.

See the LICENSE file for details.

---

# Author

**Mukhtar Aliyu**

Founder, POS Ledger NG

Thank you for using POS Ledger NG.
