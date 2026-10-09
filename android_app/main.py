import json
import threading
import urllib.request
import urllib.error

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label


API_URL = "http://127.0.0.1:8001/api/money-position"


def format_money(value):
    return f"\u20a6{float(value or 0):,.2f}"


class PosLedgerDashboard(App):

    def build(self):
        self.title = "POS Ledger NG"

        layout = BoxLayout(
            orientation="vertical",
            padding=24,
            spacing=18,
        )

        layout.add_widget(
            Label(
                text="POS LEDGER NG",
                font_size="26sp",
                bold=True,
                size_hint_y=None,
                height=65,
            )
        )

        layout.add_widget(
            Label(
                text="Financial Dashboard",
                font_size="18sp",
                size_hint_y=None,
                height=45,
            )
        )

        self.cash_label = Label(
            text="Cash: Loading...",
            font_size="22sp",
        )
        layout.add_widget(self.cash_label)

        self.wallet_label = Label(
            text="Wallet: Loading...",
            font_size="22sp",
        )
        layout.add_widget(self.wallet_label)

        self.total_label = Label(
            text="Total: Loading...",
            font_size="24sp",
            bold=True,
        )
        layout.add_widget(self.total_label)

        self.status_label = Label(
            text="Connecting to POS Ledger API...",
            font_size="14sp",
        )
        layout.add_widget(self.status_label)

        refresh_button = Button(
            text="Refresh Balances",
            size_hint_y=None,
            height=55,
        )
        refresh_button.bind(on_press=self.refresh_balances)
        layout.add_widget(refresh_button)

        return layout

    def on_start(self):
        self.refresh_balances()

    def refresh_balances(self, *args):
        self.status_label.text = "Connecting to API..."
        threading.Thread(
            target=self.fetch_balances,
            daemon=True,
        ).start()

    def fetch_balances(self):
        try:
            request = urllib.request.Request(
                API_URL,
                headers={"Accept": "application/json"},
                method="GET",
            )

            with urllib.request.urlopen(
                request,
                timeout=5,
            ) as response:
                result = json.loads(
                    response.read().decode("utf-8")
                )

            if not result.get("success"):
                raise ValueError("API did not return success.")

            data = result["data"]

            cash = float(data.get("cash", 0) or 0)
            wallet = float(data.get("wallet", 0) or 0)
            total = cash + wallet

            Clock.schedule_once(
                lambda dt: self.show_balances(
                    cash, wallet, total
                ),
                0,
            )

        except Exception as exc:
            message = str(exc)[:120]

            Clock.schedule_once(
                lambda dt, msg=message: self.show_error(msg),
                0,
            )

    def show_balances(self, cash, wallet, total):
        self.cash_label.text = (
            f"Cash: {format_money(cash)}"
        )
        self.wallet_label.text = (
            f"Wallet: {format_money(wallet)}"
        )
        self.total_label.text = (
            f"Total: {format_money(total)}"
        )
        self.status_label.text = (
            "Connected to POS Ledger API"
        )

    def show_error(self, message):
        self.status_label.text = (
            "API unavailable. Check that the server "
            "is running on port 8001."
        )
        print("Dashboard connection error:", message)


if __name__ == "__main__":
    PosLedgerDashboard().run()
