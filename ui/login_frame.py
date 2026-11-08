"""
ui/login_frame.py
─────────────────────────────────────────────────────────────
"""
import tkinter as tk

from db.connection import get_connection
from ui import theme


class LoginFrame(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ethiconsortia \u2014 Login")
        self.geometry("420x520")
        self.resizable(False, False)
        self.configure(bg=theme.DARK_NAVY)
        self._center()

        bg = tk.Frame(self, bg=theme.DARK_NAVY, width=420, height=520)
        bg.place(x=0, y=0, width=420, height=520)

        tk.Label(bg, text="ETHICONSORTIA", font=theme.font(22, "bold"),
                 fg="white", bg=theme.DARK_NAVY).place(x=0, y=30, width=420, height=35)
        tk.Label(bg, text="Sign in to your account", font=theme.font(12, slant="italic"),
                 fg=theme.SOFT_BLUE, bg=theme.DARK_NAVY).place(x=0, y=68, width=420, height=20)

        card = tk.Frame(bg, bg=theme.INPUT_BG, highlightbackground=theme.SOFT_BLUE,
                         highlightthickness=1)
        card.place(x=50, y=105, width=320, height=310)

        tk.Label(card, text="Username", font=theme.font(11, "bold"), fg=theme.DARK_NAVY,
                 bg=theme.INPUT_BG, anchor="w").place(x=20, y=25, width=280, height=18)
        self.txt_username = tk.Entry(card, font=theme.font(13), fg=theme.DARK_NAVY,
                                      bg="white", relief="solid", bd=1,
                                      highlightthickness=1, highlightbackground=theme.SOFT_BLUE)
        self.txt_username.place(x=20, y=45, width=280, height=35)

        tk.Label(card, text="Password", font=theme.font(11, "bold"), fg=theme.DARK_NAVY,
                 bg=theme.INPUT_BG, anchor="w").place(x=20, y=100, width=280, height=18)
        self.txt_password = tk.Entry(card, font=theme.font(13), fg=theme.DARK_NAVY,
                                      bg="white", relief="solid", bd=1, show="\u2022",
                                      highlightthickness=1, highlightbackground=theme.SOFT_BLUE)
        theme.add_password_toggle(self.txt_password, 20, 120, 280, 35)
        self.txt_password.bind("<Return>", lambda e: self.handle_login())

        self.lbl_status = tk.Label(card, text="", font=theme.font(11, "bold"),
                                    fg=theme.RED_ACCENT, bg=theme.INPUT_BG, anchor="center")
        self.lbl_status.place(x=20, y=168, width=280, height=18)

        btn_login = theme.make_button(card, "LOGIN", theme.MEDIUM_BLUE,
                                       hover_bg=theme.DARK_NAVY, font_size=13,
                                       command=self.handle_login)
        btn_login.place(x=20, y=196, width=280, height=40)

        tk.Label(card, text="\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 or \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
                 font=theme.font(10), fg=theme.SOFT_BLUE, bg=theme.INPUT_BG,
                 anchor="center").place(x=20, y=248, width=280, height=18)

        btn_register = theme.make_button(card, "CREATE AN ACCOUNT", theme.INPUT_BG,
                                          fg=theme.MEDIUM_BLUE, hover_bg="#dce6fa",
                                          font_size=11, bold=False,
                                          command=self.go_register)
        btn_register.place(x=20, y=272, width=280, height=30)

        tk.Label(bg, text="\u00a9 2026 Ethiconsortia", font=theme.font(10),
                 fg="#50648c", bg=theme.DARK_NAVY,
                 anchor="center").place(x=0, y=460, width=420, height=20)

    def _center(self):
        self.update_idletasks()
        w, h = 420, 520
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def go_register(self):
        self.destroy()
        from ui.register_frame import RegisterFrame
        RegisterFrame().mainloop()

    def handle_login(self):
        username = self.txt_username.get().strip()
        password = self.txt_password.get().strip()

        if not username or not password:
            self.lbl_status.configure(text="Please fill in all fields.", fg=theme.RED_ACCENT)
            return

        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT user_id, username, full_name, role FROM users "
                "WHERE username=%s AND password=%s",
                (username, password),
            )
            row = cur.fetchone()
            cur.close()

            if row:
                # Show a brief success message before switching screens.
                self.lbl_status.configure(text="Login successful!", fg="#2e7d32")
                self.update_idletasks()
                self.after(600, lambda: self._go_to_lobby(row))
            else:
                self.lbl_status.configure(text="Invalid username or password.", fg=theme.RED_ACCENT)
        except Exception as ex:
            self.lbl_status.configure(text=f"DB Error: {ex}", fg=theme.RED_ACCENT)

    def _go_to_lobby(self, row):
        self.destroy()
        from ui.room_lobby_frame import RoomLobbyFrame
        RoomLobbyFrame(row["user_id"], row["username"],
                        row["full_name"] or "", row["role"]).mainloop()


if __name__ == "__main__":
    LoginFrame().mainloop()