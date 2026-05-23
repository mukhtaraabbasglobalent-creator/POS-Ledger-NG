# 💳 POS Agent Financial Tracker System
Financial tracking and tax-ready reporting app for POS agents and small businesses.

---

## 📌 Project Overview
The POS Agent Financial Tracker System is a fintech support application designed to help POS agents and small business owners:

- Record daily transactions  
- Automatically calculate service charges  
- Monitor business cash flow  
- Generate reports for tax and auditing purposes  

This system combines financial tracking, automation, and record keeping to improve accountability and support better financial reporting.

---

## 🎯 Purpose of the Project
- Track cash in (deposits) and cash out (withdrawals)  
- Automatically calculate transaction charges  
- Show daily profit  
- Maintain total business money records (cash box + wallet)  
- Provide a simple system to support financial reporting and tax analysis  

---

## ⚙️ Core Features

### ✅ Transaction Recording
Stores transaction type, amount, date, charges, and profit earned in a **SQLite database (`pos_agent.db`)**.

### 💰 Automatic Charge Calculation
| Transaction Amount | Charge |
|------------------|-------|
| ₦1,000 – ₦9,999  | ₦100  |
| ₦10,000 – ₦19,999 | ₦200 |

### 📊 Summaries
- **Daily Summary**: Total Deposits, Withdrawals, Charges, Profit, Business Money  
- **Monthly Summary**: Same as daily, aggregated by month  

### 💾 Export Reports
Export daily or monthly transactions to **CSV files** for auditing or presentation.

---

## 🖼 Screenshots (placeholders)
- Main Menu: `screenshots/main_menu.png`  
- Add Transaction: `screenshots/add_transaction.png`  
- Daily Summary: `screenshots/daily_summary.png`  
- Monthly Summary: `screenshots/monthly_summary.png`  
- Export Confirmation: `screenshots/export.png`  

---

## 🧩 Workflow
Flow:  
**Users → Add Transaction → SQLite Database → Calculations → Summaries → Export Reports**

---

## 🧩 System Architecture

![POS Agent Tracker Architecture](ystem_architecture.png)

---

## ✅ Key Points
- **Secure Access**: PIN authentication ensures only authorized users access the system.  
- **GUI Interface**: Users interact with buttons and input fields.  
- **Automatic Calculations**: Charges and profits are calculated automatically.  
- **Daily & Monthly Summaries**: View business totals instantly.  
- **Export Reports**: Save CSV files for auditing or tax purposes.  
- **Persistent Storage**: All transactions saved in **SQLite database**.

---

## 📄 Sample Reports
- `Daily_Report_YYYY-MM-DD.csv`  
- `Monthly_Report_YYYY-MM.csv`  
Uploaded in `sample_reports/` folder for reference.

---

## 🎬 Demo Video
Watch the app in action:  
`demo/POS_Tracker_Demo.mp4` *(replace with your actual video file or link)*

---

## 💻 How to Run
1. Clone the repository:
```bash
git clone https://github.com/mukhtaraabbasglobalent-creator/POS-Agent-Tracker.git
pip install -r requirements.txt
python gui_app.py
Use the menu to:
Add Transactions
View Daily & Monthly Summaries
Export CSV Reports
🔐 Future Enhancements
Cloud-based data storage
PDF report generation
AI integration for business insights
Advanced GUI styling (themes or PyQt)
👤 Project Author
Mukhtar A Abbas Global Ent.
Focused on fintech systems, cybersecurity learning, and building practical technology solutions for business improvement.
