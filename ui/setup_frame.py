"""
ui/setup_frame.py
First-run database setup. Saves the login in the user's own app folder.
"""
import tkinter as tk

from db import connection
from db.config import save_config
from ui import theme


class SetupFrame(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ethiconsortia \u2014 Database Setup")
        self.geometry("460x620")
        self.resizable(False, False)
        self.configure(bg=theme.DARK_NAVY)
        self._center()

        bg = tk.Frame(self, bg=theme.DARK_NAVY)
        bg.place(x=0, y=0, width=460, height=620)

        tk.Label(bg, text="ETHICONSORTIA", font=theme.font(20, "bold"), fg="white",
                 bg=theme.DARK_NAVY, anchor="center").place(x=0, y=20, width=460, height=30)
        tk.Label(bg, text="Connect to the database", font=theme.font(12, slant="italic"),
                 fg=theme.SOFT_BLUE, bg=theme.DARK_NAVY,
                 anchor="center").place(x=0, y=52, width=460, height=20)

        card = tk.Frame(bg, bg=theme.INPUT_BG, highlightbackground=theme.SOFT_BLUE,
                        highlightthickness=1)
        card.place(x=40, y=85, width=380, height=490)

        cfg = connection.get_settings() or {}
        self.txt_host = self._field(card, "Server address (host)", cfg.get("host", ""), 20)
        self.txt_port = self._field(card, "Port", str(cfg.get("port", 3306)), 82)
        self.txt_db = self._field(card, "Database name",
                                  cfg.get("database", "ethiconsortia"), 144)
        self.txt_user = self._field(card, "Database user", cfg.get("user", "ethic_app"), 206)

        tk.Label(card, text="Database password", font=theme.font(11, "bold"),
                 fg=theme.DARK_NAVY, bg=theme.INPUT_BG, anchor="w").place(
            x=20, y=268, width=340, height=18)
        self.txt_password = tk.Entry(card, font=theme.font(12), fg=theme.DARK_NAVY,
                                     bg="white", relief="solid", bd=1,
                                     highlightthickness=1,
                                     highlightbackground=theme.SOFT_BLUE)
        self.txt_password.insert(0, cfg.get("password", ""))
        theme.add_password_toggle(self.txt_password, 20, 290, 340, 32)

        self.lbl_status = tk.Label(card, text="", font=theme.font(10, "bold"),
                                   bg=theme.INPUT_BG, anchor="center",
                                   wraplength=340, justify="center")
        self.lbl_status.place(x=20, y=332, width=340, height=40)

        theme.make_button(card, "TEST CONNECTION", "#28376e", font_size=12,
                          command=self._test).place(x=20, y=380, width=340, height=38)
        theme.make_button(card, "SAVE & CONTINUE", theme.MEDIUM_BLUE,
                          hover_bg=theme.DARK_NAVY, font_size=13,
                          command=self._save).place(x=20, y=428, width=340, height=38)

    def _field(self, card, label, value, y):
        tk.Label(card, text=label, font=theme.font(11, "bold"), fg=theme.DARK_NAVY,
                 bg=theme.INPUT_BG, anchor="w").place(x=20, y=y, width=340, height=18)
        e = tk.Entry(card, font=theme.font(12), fg=theme.DARK_NAVY, bg="white",
                     relief="solid", bd=1, highlightthickness=1,
                     highlightbackground=theme.SOFT_BLUE)
        e.insert(0, value)
        e.place(x=20, y=y + 22, width=340, height=32)
        return e

    def _center(self):
        self.update_idletasks()
        w, h = 460, 620
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _say(self, msg, color):
        self.lbl_status.configure(text=msg, fg=color)

    def _values(self):
        host = self.txt_host.get().strip()
        port = self.txt_port.get().strip()
        database = self.txt_db.get().strip()
        user = self.txt_user.get().strip()
        password = self.txt_password.get()
        if not host or not database or not user:
            self._say("Host, database and user are required.", theme.RED_ACCENT)
            return None
        if not port.isdigit() or not (1 <= int(port) <= 65535):
            self._say("Port must be a number from 1 to 65535.", theme.RED_ACCENT)
            return None
        return host, int(port), database, user, password

    def _try_connect(self, vals):
        self._say("Testing\u2026", theme.MEDIUM_BLUE)
        self.update_idletasks()
        ok, msg = connection.test_connection(*vals)
        if ok:
            self._say("\u2713 Connected.", theme.SUCCESS)
        else:
            self._say(f"Can't connect: {msg[:120]}", theme.RED_ACCENT)
        return ok

    def _test(self):
        vals = self._values()
        if vals:
            self._try_connect(vals)

    def _save(self):
        vals = self._values()
        if not vals or not self._try_connect(vals):
            return
        try:
            save_config(*vals)
        except OSError as ex:
            self._say(f"Can't save settings: {ex}", theme.RED_ACCENT)
            return
        connection.reset_connection()
        self.destroy()
        from ui.login_frame import LoginFrame
        LoginFrame().mainloop()