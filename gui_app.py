import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
import csv
from database import add_transaction, get_all_transactions
from calculations import calculate_charge_and_profit

# ================== CONFIG ===================
PIN_CODE = "1234"  # Change this to your secure PIN
# ============================================

# ======== GUI APP ========
class POSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("POS Agent Tracker")
        self.root.geometry("500x400")
        self.current_user_authenticated = False

        self.show_pin_screen()

    # ---------- PIN SCREEN ----------
    def show_pin_screen(self):
        self.clear_frame()
        tk.Label(self.root, text="Enter 4-digit PIN", font=("Arial", 16)).pack(pady=20)
        self.pin_entry = tk.Entry(self.root, show="*", font=("Arial", 14))
        self.pin_entry.pack(pady=10)
        tk.Button(self.root, text="Submit", command=self.check_pin).pack(pady=10)

    def check_pin(self):
        entered_pin = self.pin_entry.get()
        if entered_pin == PIN_CODE:
            self.current_user_authenticated = True
            self.show_main_menu()
        else:
            messagebox.showerror("Error", "Incorrect PIN!")

    # ---------- MAIN MENU ----------
    def show_main_menu(self):
        self.clear_frame()
        tk.Label(self.root, text="POS Agent Tracker", font=("Arial", 16, "bold")).pack(pady=20)

        buttons = [
            ("Add Transaction", self.show_add_transaction),
            ("Daily Summary", self.show_daily_summary),
            ("Monthly Summary", self.show_monthly_summary),
            ("Export Daily Report", lambda: self.export_report("daily")),
            ("Export Monthly Report", lambda: self.export_report("monthly")),
            ("Exit", self.root.quit)
        ]

        for text, cmd in buttons:
            tk.Button(self.root, text=text, width=30, command=cmd).pack(pady=5)

    # ---------- ADD TRANSACTION ----------
    def show_add_transaction(self):
        self.clear_frame()
        tk.Label(self.root, text="Add Transaction", font=("Arial", 16)).pack(pady=10)

        tk.Label(self.root, text="Type (Deposit/Withdrawal)").pack()
        self.type_entry = ttk.Combobox(self.root, values=["Deposit", "Withdrawal"])
        self.type_entry.pack()

        tk.Label(self.root, text="Amount").pack()
        self.amount_entry = tk.Entry(self.root)
        self.amount_entry.pack()

        tk.Label(self.root, text="Cash Box or Wallet").pack()
        self.location_entry = ttk.Combobox(self.root, values=["Cash Box", "Wallet"])
        self.location_entry.pack()

        tk.Label(self.root, text="Description").pack()
        self.description_entry = tk.Entry(self.root)
        self.description_entry.pack()

        tk.Button(self.root, text="Submit", command=self.submit_transaction).pack(pady=10)
        tk.Button(self.root, text="Back", command=self.show_main_menu).pack()

    def submit_transaction(self):
        t_type = self.type_entry.get()
        try:
            amount = float(self.amount_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Amount must be a number")
            return
        location = self.location_entry.get()
        description = self.description_entry.get()

        charge, profit = calculate_charge_and_profit(amount)
        add_transaction(t_type, amount, location, description, charge, profit)
        messagebox.showinfo("Success", f"Transaction added!\nCharge: ₦{charge}\nProfit: ₦{profit}")
        self.show_main_menu()

    # ---------- SUMMARIES ----------
    def show_daily_summary(self):
        self.clear_frame()
        tk.Label(self.root, text="Daily Summary", font=("Arial", 16)).pack(pady=10)

        transactions = get_all_transactions()
        today = datetime.now().date()
        total_deposit = total_withdrawal = total_charge = total_profit = 0

        for tx in transactions:
            if tx["date"].date() == today:
                if tx["type"] == "Deposit":
                    total_deposit += tx["amount"]
                else:
                    total_withdrawal += tx["amount"]
                total_charge += tx["charge"]
                total_profit += tx["profit"]

        summary_text = (
            f"Total Deposit: ₦{total_deposit}\n"
            f"Total Withdrawal: ₦{total_withdrawal}\n"
            f"Total Charges: ₦{total_charge}\n"
            f"Total Profit: ₦{total_profit}"
        )
        tk.Label(self.root, text=summary_text, font=("Arial", 12)).pack(pady=10)
        tk.Button(self.root, text="Back", command=self.show_main_menu).pack()

    def show_monthly_summary(self):
        self.clear_frame()
        tk.Label(self.root, text="Monthly Summary", font=("Arial", 16)).pack(pady=10)

        transactions = get_all_transactions()
        today = datetime.now()
        total_deposit = total_withdrawal = total_charge = total_profit = 0

        for tx in transactions:
            if tx["date"].year == today.year and tx["date"].month == today.month:
                if tx["type"] == "Deposit":
                    total_deposit += tx["amount"]
                else:
                    total_withdrawal += tx["amount"]
                total_charge += tx["charge"]
                total_profit += tx["profit"]

        summary_text = (
            f"Total Deposit: ₦{total_deposit}\n"
            f"Total Withdrawal: ₦{total_withdrawal}\n"
            f"Total Charges: ₦{total_charge}\n"
            f"Total Profit: ₦{total_profit}"
        )
        tk.Label(self.root, text=summary_text, font=("Arial", 12)).pack(pady=10)
        tk.Button(self.root, text="Back", command=self.show_main_menu).pack()

    # ---------- EXPORT REPORT ----------
    def export_report(self, period="daily"):
        transactions = get_all_transactions()
        today = datetime.now()
        filename = ""

        if period == "daily":
            filename = f"Daily_Report_{today.strftime('%Y-%m-%d')}.csv"
            filtered = [tx for tx in transactions if tx["date"].date() == today.date()]
        else:
            filename = f"Monthly_Report_{today.strftime('%Y-%m')}.csv"
            filtered = [tx for tx in transactions if tx["date"].year == today.year and tx["date"].month == today.month]

        if not filtered:
            messagebox.showinfo("Info", "No transactions to export")
            return

        with open(filename, "w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["type", "amount", "location", "description", "charge", "profit", "date"])
            writer.writeheader()
            for tx in filtered:
                writer.writerow({
                    "type": tx["type"],
                    "amount": tx["amount"],
                    "location": tx["location"],
                    "description": tx["description"],
                    "charge": tx["charge"],
                    "profit": tx["profit"],
                    "date": tx["date"].strftime("%Y-%m-%d %H:%M:%S")
                })

        messagebox.showinfo("Success", f"{filename} exported successfully!")

    # ---------- UTILITY ----------
    def clear_frame(self):
        for widget in self.root.winfo_children():
            widget.destroy()

# ===== RUN APP =====
if __name__ == "__main__":
    root = tk.Tk()
    app = POSApp(root)
    root.mainloop()
