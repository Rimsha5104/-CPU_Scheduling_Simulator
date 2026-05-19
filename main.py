"""Launcher for the Real-Time Interactive CPU Scheduling Simulator."""

from ui import SchedulingSimulatorApp


def main() -> None:
    """Create the desktop app and start the Tkinter event loop."""
    simulator_app = SchedulingSimulatorApp()
    simulator_app.mainloop()


if __name__ == "__main__":
    main()
