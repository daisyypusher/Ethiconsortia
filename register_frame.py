"""
ui/register_frame.py
─────────────────────────────────────────────────────────────
"""
import tkinter as tk
from tkinter import ttk

from db.connection import get_connection
from ui import theme


class RegisterFrame(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ethiconsortia \u2014 Create Account")
        self.geometry("460x680")
        self.resizable(False, False)
        self.configure(bg=theme.DARK_NAVY)
        self._center()

        bg = tk.Frame(self, bg=theme.DARK_NAVY)
        bg.place(x=0, y=0, width=460, height=680)

        tk.Label(bg, text="ETHICONSORTIA", font=theme.font(20, "bold"), fg="white",
                 bg=theme.DARK_NAVY, anchor="center").place(x=0, y=20, width=460, height=30)
        tk.Label(bg, text="Create your account", font=theme.font(12, slant="italic"),
                 fg=theme.SOFT_BLUE, bg=theme.DARK_NAVY,
                 anchor="center").place(x=0, y=52, width=460, height=20)

        card = tk.Frame(bg, bg=theme.INPUT_BG, highlightbackground=theme.SOFT_BLUE,
                         highlightthickness=1)
        card.place(x=40, y=85, width=380, height=520)

        y = 20
        fw, fx = 340, 20

        self._card_label(card, "Account Type", fx, y)
        y += 22
        self.cmb_role = ttk.Combobox(card, values=["Student", "Professor", "Administrator"],
                                      state="readonly", font=theme.font(12))
        self.cmb_role.current(0)
        self.cmb_role.place(x=fx, y=y, width=fw, height=32)
        self.cmb_role.bind("<<ComboboxSelected>>", self._on_role_change)
        y += 42

        # ── Verification panel (hidden by default) ──
        self.verify_panel = tk.Frame(card, bg="#fff8dc", highlightbackground=theme.WARN_YELLOW,
                                      highlightthickness=1)
        self._verify_y = y
        tk.Label(self.verify_panel, text="\U0001F512 Verification Required",
                 font=theme.font(11, "bold"), fg="#825a00", bg="#fff8dc",
                 anchor="w").place(x=10, y=5, width=320, height=18)
        self.lbl_verify_hint = tk.Label(self.verify_panel, text="Enter your Professor access code:",
                                         font=theme.font(10), fg="#644600", bg="#fff8dc", anchor="w")
        self.lbl_verify_hint.place(x=10, y=24, width=320, height=14)
        self.txt_verify_code = tk.Entry(self.verify_panel, font=theme.font(12),
                                         bg="white", fg=theme.DARK_NAVY, relief="solid", bd=1,
                                         highlightthickness=1, highlightbackground=theme.WARN_YELLOW)
        self.txt_verify_code.place(x=10, y=42, width=320, height=28)
        # not placed on the card yet -> hidden
        y += 90

        self._card_label(card, "Full Name", fx, y)
        y += 22
        self.txt_full_name = theme.placeholder_entry(card, "e.g. Juan Dela Cruz")
        self.txt_full_name.place(x=fx, y=y, width=fw, height=32)
        y += 42

        self._card_label(card, "Username", fx, y)
        y += 22
        self.txt_username = theme.placeholder_entry(card, "e.g. jdelacruz")
        self.txt_username.place(x=fx, y=y, width=fw, height=32)
        y += 42

        self._card_label(card, "Password", fx, y)
        y += 22
        self.txt_password = tk.Entry(card, font=theme.font(12), fg=theme.DARK_NAVY,
                                      bg="white", relief="solid", bd=1, show="\u2022",
                                      highlightthickness=1, highlightbackground=theme.SOFT_BLUE)
        theme.add_password_toggle(self.txt_password, fx, y, fw, 32)
        y += 42

        self._card_label(card, "Confirm Password", fx, y)
        y += 22
        self.txt_confirm = tk.Entry(card, font=theme.font(12), fg=theme.DARK_NAVY,
                                     bg="white", relief="solid", bd=1, show="\u2022",
                                     highlightthickness=1, highlightbackground=theme.SOFT_BLUE)
        theme.add_password_toggle(self.txt_confirm, fx, y, fw, 32)
        y += 50

        self.lbl_status = tk.Label(card, text="", font=theme.font(11, "bold"),
                                    bg=theme.INPUT_BG, anchor="center")
        self.lbl_status.place(x=fx, y=y, width=fw, height=20)
        y += 28

        btn_register = theme.make_button(card, "CREATE ACCOUNT", theme.MEDIUM_BLUE,
                                          hover_bg=theme.DARK_NAVY, font_size=13,
                                          command=self.handle_register)
        btn_register.place(x=fx, y=y, width=fw, height=38)

        btn_back = tk.Button(bg, text="\u2190 Back to Login", font=theme.font(11),
                              fg=theme.SOFT_BLUE, bg=theme.DARK_NAVY, relief="flat", bd=0,
                              activebackground=theme.DARK_NAVY, activeforeground="white",
                              cursor="hand2", command=self.go_login)
        btn_back.place(x=130, y=620, width=200, height=30)

    def _card_label(self, card, text, x, y):
        tk.Label(card, text=text, font=theme.font(11, "bold"), fg=theme.DARK_NAVY,
                 bg=theme.INPUT_BG, anchor="w").place(x=x, y=y, width=340, height=18)

    def _center(self):
        self.update_idletasks()
        w, h = 460, 680
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _on_role_change(self, _e=None):
        selected = self.cmb_role.get()
        needs_verify = selected in ("Professor", "Administrator")
        self.txt_verify_code.delete(0, tk.END)
        if needs_verify:
            self.verify_panel.place(x=20, y=self._verify_y, width=340, height=80)
            hint = "Enter your Professor access code:" if selected == "Professor" \
                else "Enter your Administrator access code:"
            self.lbl_verify_hint.configure(text=hint)
        else:
            self.verify_panel.place_forget()

    def go_login(self):
        self.destroy()
        from ui.login_frame import LoginFrame
        LoginFrame().mainloop()

    def set_status(self, msg, color):
        self.lbl_status.configure(text=msg, fg=color)

    def handle_register(self):
        full_name = theme.entry_value(self.txt_full_name)
        username = theme.entry_value(self.txt_username)
        password = self.txt_password.get().strip()
        confirm = self.txt_confirm.get().strip()
        role = self.cmb_role.get().lower()
        ver_code = self.txt_verify_code.get().strip()

        if not full_name or not username or not password or not confirm:
            self.set_status("Please fill in all fields.", theme.RED_ACCENT)
            return
        if len(username) < 3:
            self.set_status("Username must be at least 3 characters.", theme.RED_ACCENT)
            return
        if len(password) < 8:
            self.set_status("Password must be at least 8 characters.", theme.RED_ACCENT)
            return
        if password != confirm:
            self.set_status("Passwords do not match.", theme.RED_ACCENT)
            return

        if role in ("professor", "administrator"):
            if not ver_code:
                self.set_status("Verification code is required.", theme.RED_ACCENT)
                return
            check_role = "admin" if role == "administrator" else "professor"
            if not self._check_verification_code(check_role, ver_code):
                self.set_status("Invalid verification code.", theme.RED_ACCENT)
                return

        if self._is_username_taken(username):
            self.set_status("Username is already taken.", theme.RED_ACCENT)
            return

        try:
            conn = get_connection()
            cur = conn.cursor()
            db_role = "admin" if role == "administrator" else role
            cur.execute(
                "INSERT INTO users (full_name, username, password, role) "
                "VALUES (%s, %s, %s, %s)",
                (full_name, username, password, db_role),
            )
            cur.close()
            self.set_status("Account created successfully!", theme.SUCCESS)
            self.after(1500, self.go_login)
        except Exception as ex:
            self.set_status(f"DB Error: {ex}", theme.RED_ACCENT)

    def _check_verification_code(self, role, code):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM verification_codes WHERE role=%s AND code=%s AND is_active=1",
                (role, code),
            )
            row = cur.fetchone()
            cur.close()
            return row is not None
        except Exception:
            return False

    def _is_username_taken(self, username):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM users WHERE username=%s", (username,))
            row = cur.fetchone()
            cur.close()
            return row is not None
        except Exception:
            return False


if __name__ == "__main__":
    RegisterFrame().mainloop()