"""Thin launcher for the STM32 smart-fan dashboard."""

from dashboard_app import FanDashboardApp


def main() -> None:
    app = FanDashboardApp()
    app.mainloop()


if __name__ == "__main__":
    main()
