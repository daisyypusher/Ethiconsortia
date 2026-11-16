r"""
main.py
──────────────────────────────────────────────────────────────────────────
Run with:   python ethiconsortia_py\main.py or py ethiconsortia_py\main.py
──────────────────────────────────────────────────────────────────────────
"""

from db.connection import get_settings
from ui.login_frame import LoginFrame
from ui.setup_frame import SetupFrame


def main():
    if get_settings() is None:
        SetupFrame().mainloop()
    else:
        LoginFrame().mainloop()


if __name__ == "__main__":
    main()
