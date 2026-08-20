from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label


class POSLedgerNGApp(App):
    def build(self):
        layout = BoxLayout(
            orientation="vertical",
            padding=30,
            spacing=20
        )

        layout.add_widget(
            Label(
                text="POS Ledger NG",
                font_size="32sp"
            )
        )

        layout.add_widget(
            Label(
                text="Android build test successful",
                font_size="20sp"
            )
        )

        return layout


if __name__ == "__main__":
    POSLedgerNGApp().run()
