"""
ui/room_lobby_frame.py
─────────────────────────────────────────────────────────────
"""
import tkinter as tk
from tkinter import messagebox
import uuid

from db.connection import get_connection
from ui import theme


class RoomLobbyFrame(tk.Tk):
    def __init__(self, user_id, username, full_name, role):
        super().__init__()
        self.current_user_id = user_id
        self.current_username = username
        self.current_full_name = full_name
        self.current_role = role

        self.title("Ethiconsortia \u2014 Lobby")
        self.geometry("960x640")
        self.resizable(False, False)
        self.configure(bg=theme.DARK_NAVY)
        self._center()

        main = tk.Frame(self, bg=theme.DARK_NAVY)
        main.place(x=0, y=0, width=960, height=640)

        # ── Top bar ──
        top_bar = tk.Frame(main, bg=theme.DARKER_NAVY)
        top_bar.place(x=0, y=0, width=960, height=55)

        tk.Label(top_bar, text="ETHICONSORTIA", font=theme.font(20, "bold"),
                 fg="white", bg=theme.DARKER_NAVY, anchor="w").place(x=20, y=14, width=250, height=28)

        role_label = theme.role_label(role)
        tk.Label(top_bar, text=f"{theme.role_emoji(role)}  {self._display_name()}  |  {role_label}",
                 font=theme.font(12, emoji=True), fg=theme.SOFT_BLUE, bg=theme.DARKER_NAVY,
                 anchor="w").place(x=280, y=18, width=450, height=20)

        btn_logout = theme.make_button(top_bar, "Logout", theme.RED_ACCENT, font_size=11,
                                        bold=False, command=self._logout)
        btn_logout.place(x=870, y=14, width=72, height=28)

        self.btn_notify = None
        if role == "professor":
            self.btn_notify = theme.make_button(top_bar, "\u2709 Messages", "#28376e",
                                                 font_size=10, bold=False, emoji=True,
                                                 command=self._show_dm_previews)
            self.btn_notify.place(x=735, y=14, width=125, height=28)
            self._poll_notifications()

        # ── Left sidebar (room quick icons) ──
        self.sidebar = tk.Frame(main, bg=theme.DARKER_NAVY)
        self.sidebar.place(x=0, y=55, width=72, height=585)
        
        # ── Archived rooms button (bottom-left, only shown when there is something to see) ──
        self.btn_archived = theme.make_button(
            main, "\U0001F4E6\nArchived", "#28376e", font_size=9, emoji=True,
            command=self.show_archived_rooms_dialog)
        
        # ── Main content ──
        content = tk.Frame(main, bg=theme.DARK_NAVY)
        content.place(x=72, y=55, width=888, height=585)

        first_name = self.current_full_name.split(" ")[0] if self.current_full_name else self.current_username
        tk.Label(content, text=f"Welcome back, {first_name}!", font=theme.font(28, "bold"),
                 fg="white", bg=theme.DARK_NAVY,
                 anchor="center").place(x=0, y=25, width=888, height=42)
        tk.Label(content, text="Select a room to enter, or create / join a new one.",
                 font=theme.font(13, slant="italic"), fg=theme.SOFT_BLUE, bg=theme.DARK_NAVY,
                 anchor="center").place(x=0, y=70, width=888, height=22)

        tk.Label(content, text="YOUR ROOMS", font=theme.font(11, "bold"), fg="#8ca5d2",
                 bg=theme.DARK_NAVY, anchor="w").place(x=44, y=110, width=800, height=18)

        rooms_outer = tk.Frame(content, bg=theme.ROOMS_BG, highlightbackground=theme.MEDIUM_BLUE,
                                highlightthickness=1)
        rooms_outer.place(x=44, y=132, width=800, height=230)

        rooms_canvas = tk.Canvas(rooms_outer, bg=theme.ROOMS_BG, highlightthickness=0)
        h_scroll = tk.Scrollbar(rooms_outer, orient="horizontal", command=rooms_canvas.xview)
        rooms_canvas.configure(xscrollcommand=h_scroll.set)
        h_scroll.pack(side="bottom", fill="x")
        rooms_canvas.pack(side="top", fill="both", expand=True)

        self.rooms_list_panel = tk.Frame(rooms_canvas, bg=theme.ROOMS_BG)
        rooms_canvas.create_window((0, 0), window=self.rooms_list_panel, anchor="nw")
        self.rooms_list_panel.bind(
            "<Configure>",
            lambda e: rooms_canvas.configure(scrollregion=rooms_canvas.bbox("all")),
        )

        if self.current_role == "admin":
            # Admins get 3 buttons: Create Room, Join Room, Join Department
            btn_create = theme.make_button(content, "\uff0b   Create Room", theme.MEDIUM_BLUE,
                                            hover_bg=theme.darker(theme.MEDIUM_BLUE), font_size=13,
                                            emoji=True, command=self.show_create_room_dialog)
            btn_create.place(x=109, y=392, width=210, height=58)

            btn_join = theme.make_button(content, "\U0001F517   Join Room", theme.GREEN_BTN,
                                          hover_bg=theme.darker(theme.GREEN_BTN), font_size=13,
                                          emoji=True, command=self.show_join_room_dialog)
            btn_join.place(x=339, y=392, width=210, height=58)

            btn_dept = theme.make_button(content, "\U0001F3DB   Join Department", theme.DM_BADGE_BG,
                                          hover_bg=theme.darker(theme.DM_BADGE_BG), font_size=13,
                                          emoji=True, command=self.show_join_department_dialog)
            btn_dept.place(x=569, y=392, width=210, height=58)

            btn_leave_dept = tk.Button(content, text="Leave a Department", font=theme.font(11),
                                        fg=theme.SOFT_BLUE, bg=theme.DARK_NAVY, relief="flat",
                                        bd=0, cursor="hand2", activebackground=theme.DARK_NAVY,
                                        activeforeground="white",
                                        command=self.show_leave_department_dialog)
            btn_leave_dept.place(x=569, y=458, width=210, height=26)
        else:
            btn_create = theme.make_button(content, "\uff0b   Create Room", theme.MEDIUM_BLUE,
                                            hover_bg=theme.darker(theme.MEDIUM_BLUE), font_size=15,
                                            emoji=True, command=self.show_create_room_dialog)
            btn_create.place(x=180, y=392, width=210, height=58)

            tk.Label(content, text="\u2014 or \u2014", font=theme.font(12), fg="#6482b4",
                     bg=theme.DARK_NAVY, anchor="center").place(x=395, y=407, width=98, height=22)

            btn_join = theme.make_button(content, "\U0001F517   Join Room", theme.GREEN_BTN,
                                          hover_bg=theme.darker(theme.GREEN_BTN), font_size=15,
                                          emoji=True, command=self.show_join_room_dialog)
            btn_join.place(x=498, y=392, width=210, height=58)

        self.refresh_rooms()

    # ── Public refresh method (called by RoomFrame on back) ──
    def refresh_rooms(self):
        for w in self.rooms_list_panel.winfo_children():
            w.destroy()
        for w in self.sidebar.winfo_children():
            w.destroy()
        self._rebuild_sidebar_divider()

        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT r.room_id, r.room_name, r.description, r.host_id, r.invite_code,
                       r.is_archived,
                       COALESCE(rm.room_role, 'member') AS room_role
                FROM rooms r
                LEFT JOIN room_members rm
                       ON r.room_id = rm.room_id AND rm.user_id = %s
                WHERE (rm.user_id IS NOT NULL
                       OR r.department_id IN (
                            SELECT department_id FROM admin_departments WHERE user_id = %s))
                  AND r.is_archived = 0
                ORDER BY r.created_at ASC
                """,
                (self.current_user_id, self.current_user_id),
            )
            rows = cur.fetchall()
            cur.close()

            # show the bottom-left button only if this host/admin has archived rooms
            try:
                n_arch = len(self._fetch_archived_rooms())
            except Exception:
                n_arch = 0
            if n_arch:
                self.btn_archived.configure(text=f"\U0001F4E6 {n_arch}\nArchived")
                self.btn_archived.place(x=4, y=588, width=64, height=44)
            else:
                self.btn_archived.place_forget()

            side_y = 15
            col, row = 0, 0
            max_cols = 3

            for r in rows:
                effective_role = r["room_role"]
                desc = r["description"]

                card = self._build_room_card(r["room_id"], r["room_name"], desc,
                                              effective_role, r["invite_code"], r["host_id"])
                card.grid(row=row, column=col, padx=7, pady=7)
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

                icon = self._build_sidebar_icon(r["room_name"], r["room_id"], r["room_name"],
                                                 effective_role, r["host_id"])
                icon.place(x=13, y=side_y, width=46, height=46)
                side_y += 58

            if not rows:
                empty = tk.Label(
                    self.rooms_list_panel,
                    text="No rooms yet.\nCreate or join one below!",
                    font=theme.font(13, slant="italic"), fg="#78a0c8", bg=theme.ROOMS_BG,
                    justify="center",
                )
                empty.place(x=0, y=0, width=790, height=202)

        except Exception as ex:
            print(f"Error loading rooms: {ex}")

    def _rebuild_sidebar_divider(self):
        sep = tk.Frame(self.sidebar, bg=theme.MEDIUM_BLUE, height=3)
        sep.place(x=10, y=8, width=52, height=3)

    def _build_room_card(self, r_id, name, desc, r_role, inv_code, host_id):
        card = tk.Frame(self.rooms_list_panel, width=190, height=200, bg=theme.ROOM_CARD_BG,
                         highlightbackground=theme.MEDIUM_BLUE, highlightthickness=1,
                         cursor="hand2")
        card.pack_propagate(False)

        icon_canvas = theme.RoundedCanvas(card, width=60, height=60, bg=theme.ROOM_CARD_BG,
                                           highlightthickness=0)
        icon_canvas.place(x=65, y=14)
        icon_canvas.rounded_rect(0, 0, 60, 60, radius=12, fill=theme.MEDIUM_BLUE, outline="")
        icon_canvas.create_text(30, 30, text=name[0].upper(), fill="white",
                                 font=theme.font(30, "bold"))

        display_name = (name[:20] + "\u2026") if len(name) > 20 else name
        tk.Label(card, text=display_name, font=theme.font(12, "bold"), fg="white",
                 bg=theme.ROOM_CARD_BG, anchor="center").place(x=5, y=82, width=180, height=18)

        short_desc = "No description" if not desc else (
            (desc[:45] + "\u2026") if len(desc) > 45 else desc)
        tk.Label(card, text=short_desc, font=theme.font(10, slant="italic"), fg=theme.SOFT_BLUE,
                 bg=theme.ROOM_CARD_BG, anchor="center", justify="center",
                 wraplength=170).place(x=5, y=102, width=180, height=28)

        pill_text = "HOST" if r_role == "host" else "MEMBER"
        pill_color = theme.RED_ACCENT if r_role == "host" else theme.MEDIUM_BLUE
        tk.Label(card, text=pill_text, font=theme.font(9, "bold"), fg="white", bg=pill_color,
                 anchor="center").place(x=55, y=136, width=80, height=17)

        if r_role == "host" or self.current_role == "admin":
            tk.Label(card, text=f"Code: {inv_code}", font=theme.font(9, "bold"), fg="#b4d2ff",
                     bg=theme.ROOM_CARD_BG, anchor="center").place(x=5, y=157, width=180, height=14)

        enter_btn = tk.Button(card, text="Enter Room \u2192", font=theme.font(9, "bold"),
                               fg="white", bg="#3c5aa0", relief="flat", bd=0,
                               highlightbackground=theme.SOFT_BLUE, highlightthickness=1,
                               cursor="hand2",
                               command=lambda: self.enter_room(r_id, name, r_role, host_id))
        enter_btn.place(x=30, y=174, width=130, height=20)

        def enter(_e=None):
            self.enter_room(r_id, name, r_role, host_id)

        card.bind("<Enter>", lambda e: card.configure(bg="#375087"))
        card.bind("<Leave>", lambda e: card.configure(bg=theme.ROOM_CARD_BG))
        card.bind("<Button-1>", enter)

        return card

    def _build_sidebar_icon(self, first_letter, r_id, name, r_role, host_id):
        canvas = theme.RoundedCanvas(self.sidebar, width=46, height=46, bg=theme.DARKER_NAVY,
                                      highlightthickness=0, cursor="hand2")
        bg_color = {"c": "#324882"}
        shape = canvas.rounded_rect(0, 0, 46, 46, radius=14, fill=bg_color["c"], outline="")
        text = canvas.create_text(23, 23, text=first_letter[0].upper(), fill="white",
                                   font=theme.font(18, "bold"))

        def on_enter(_e):
            canvas.itemconfigure(shape, fill=theme.MEDIUM_BLUE)

        def on_leave(_e):
            canvas.itemconfigure(shape, fill=bg_color["c"])

        def on_click(_e):
            self.enter_room(r_id, name, r_role, host_id)

        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)
        canvas.bind("<Button-1>", on_click)
        return canvas

    # ── CREATE ROOM DIALOG ──
    def show_create_room_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Create a New Room")
        dlg.geometry("420x450")
        dlg.transient(self)
        dlg.grab_set()
        dlg.configure(bg=theme.ROOMS_BG)
        dlg.resizable(False, False)

        tk.Label(dlg, text="Create a New Room", font=theme.font(16, "bold"), fg="white",
                 bg=theme.ROOMS_BG, anchor="w").place(x=20, y=15, width=380, height=26)

        self._dlg_label(dlg, "Room Name *", 20, 55)
        tf_name = self._dlg_field(dlg, 20, 76, 380)

        self._dlg_label(dlg, "Description (optional)", 20, 120)
        tf_desc = self._dlg_field(dlg, 20, 141, 380)

        self._dlg_label(dlg, "Department Name *", 20, 185)
        tf_dept_name = self._dlg_field(dlg, 20, 206, 380)

        self._dlg_label(dlg, "Department ID *", 20, 250)
        tf_dept_id = self._dlg_field(dlg, 20, 271, 380)

        lbl_status = tk.Label(dlg, text="", font=theme.font(11), fg=theme.RED_ACCENT,
                               bg=theme.ROOMS_BG, anchor="center")
        lbl_status.place(x=20, y=320, width=380, height=18)

        def do_create():
            name = tf_name.get().strip()
            desc = tf_desc.get().strip()
            dept_name = tf_dept_name.get().strip()
            dept_id = tf_dept_id.get().strip()
            if not name:
                lbl_status.configure(text="Room name is required.")
                return
            if len(name) > 50:
                lbl_status.configure(text="Name too long (max 50 chars).")
                return
            if not dept_name or not dept_id:
                lbl_status.configure(text="Department name and ID are required.")
                return
            # ⬇ keep whatever call matches YOUR _do_create_room signature
            self._do_create_room(name=name, desc=desc, dept_name=dept_name,
                                 dept_id=dept_id, dlg=dlg)

        btn_ok = self._dialog_button(dlg, "Create Room", theme.MEDIUM_BLUE, do_create)
        btn_ok.place(x=100, y=346, width=220, height=40)

        btn_cancel = self._ghost_button(dlg, "Cancel", dlg.destroy)
        btn_cancel.place(x=150, y=394, width=120, height=26)

    def _do_create_room(self, name, desc, dept_name, dept_id, dlg):
        try:
            conn = get_connection()
            cur = conn.cursor()

            code = uuid.uuid4().hex[:8].upper()
            while self._code_exists(cur, code):
                code = uuid.uuid4().hex[:8].upper()

            cur.execute(
                "INSERT INTO rooms (room_name, description, host_id, invite_code, "
                "department_name, department_id) VALUES (%s, %s, %s, %s, %s, %s)",
                (name, desc, self.current_user_id, code, dept_name, dept_id),
            )
            room_id = cur.lastrowid

            cur.execute(
                "INSERT INTO room_members (room_id, user_id, room_role, can_send_messages, "
                "can_read_history, can_manage_members) VALUES (%s, %s, 'host', 1, 1, 1)",
                (room_id, self.current_user_id),
            )

            # admins monitor the department of any room they create
            if self.current_role == "admin":
                cur.execute(
                    "INSERT IGNORE INTO admin_departments (user_id, department_id) "
                    "VALUES (%s, %s)", (self.current_user_id, dept_id))

            sub_rooms = [("General", "text", 0), ("Announcements", "announcement", 1)]
            for sr_name, sr_type, pos in sub_rooms:
                is_ann = sr_type == "announcement"
                cur.execute(
                    "INSERT INTO room_sub_rooms (room_id, sub_room_name, sub_room_type, position, "
                    "everyone_send, everyone_upload) VALUES (%s, %s, %s, %s, %s, %s)",
                    (room_id, sr_name, sr_type, pos, 0 if is_ann else 1, 0 if is_ann else 1),
                )

            dlg.destroy()
            messagebox.showinfo(
                "Room Created \u2713",
                f'Room "{name}" created!\n\nInvite Code:  {code}\n\n'
                "Share this code with others so they can join.",
                parent=self,
            )
            self.refresh_rooms()
            self.enter_room(room_id, name, "host", self.current_user_id)

        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=dlg)

    def _code_exists(self, cur, code):
        cur.execute("SELECT room_id FROM rooms WHERE invite_code=%s", (code,))
        return cur.fetchone() is not None

    # ── JOIN DEPARTMENT DIALOG (admin only) ──
    def show_join_department_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Join a Department")
        dlg.geometry("400x240")
        dlg.transient(self)
        dlg.grab_set()
        dlg.configure(bg=theme.ROOMS_BG)
        dlg.resizable(False, False)

        tk.Label(dlg, text="Join a Department", font=theme.font(16, "bold"), fg="white",
                 bg=theme.ROOMS_BG, anchor="w").place(x=20, y=15, width=360, height=26)
        tk.Label(dlg, text="Enter the Department ID to monitor all of its rooms:",
                 font=theme.font(11), fg=theme.SOFT_BLUE, bg=theme.ROOMS_BG,
                 anchor="w").place(x=20, y=50, width=360, height=18)

        tf_dept = tk.Entry(dlg, font=theme.font(15, "bold"), justify="center", bg="white",
                            fg=theme.DARK_NAVY, relief="solid", bd=1,
                            highlightthickness=1, highlightbackground=theme.SOFT_BLUE)
        tf_dept.place(x=20, y=72, width=360, height=38)

        lbl_status = tk.Label(dlg, text="", font=theme.font(11), fg=theme.RED_ACCENT,
                               bg=theme.ROOMS_BG, anchor="center")
        lbl_status.place(x=20, y=118, width=360, height=18)

        def do_join_dept():
            dept_id = tf_dept.get().strip().upper()
            if not dept_id:
                lbl_status.configure(text="Please enter a Department ID.")
                return
            try:
                conn = get_connection()
                cur = conn.cursor(dictionary=True)
                cur.execute(
                    "SELECT MAX(department_name) AS dname, COUNT(*) AS n "
                    "FROM rooms WHERE department_id=%s", (dept_id,))
                info = cur.fetchone()
                if not info or info["n"] == 0:
                    lbl_status.configure(text="No rooms found for that Department ID.")
                    cur.close()
                    return
                cur.execute(
                    "INSERT IGNORE INTO admin_departments (user_id, department_id) "
                    "VALUES (%s, %s)", (self.current_user_id, dept_id))
                cur.close()

                dlg.destroy()
                self.refresh_rooms()
                messagebox.showinfo(
                    "Department Joined \u2713",
                    f'You can now see {info["n"]} room(s) in "{info["dname"]}" ({dept_id}).',
                    parent=self)
            except Exception as ex:
                lbl_status.configure(text=f"DB Error: {ex}")

        btn_ok = self._dialog_button(dlg, "Join Department", theme.GREEN_BTN, do_join_dept)
        btn_ok.place(x=100, y=142, width=200, height=40)
        tf_dept.bind("<Return>", lambda e: do_join_dept())

        btn_cancel = self._ghost_button(dlg, "Cancel", dlg.destroy)
        btn_cancel.place(x=140, y=190, width=120, height=26)

    # ── JOIN ROOM DIALOG ──
    def show_join_room_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Join a Room")
        dlg.geometry("400x240")
        dlg.transient(self)
        dlg.grab_set()
        dlg.configure(bg=theme.ROOMS_BG)
        dlg.resizable(False, False)

        tk.Label(dlg, text="Join a Room", font=theme.font(16, "bold"), fg="white",
                 bg=theme.ROOMS_BG, anchor="w").place(x=20, y=15, width=360, height=26)
        tk.Label(dlg, text="Enter the invite code shared by the room host:",
                 font=theme.font(11), fg=theme.SOFT_BLUE, bg=theme.ROOMS_BG,
                 anchor="w").place(x=20, y=50, width=360, height=18)

        tf_code = tk.Entry(dlg, font=theme.font(17, "bold"), justify="center", bg="white",
                            fg=theme.DARK_NAVY, relief="solid", bd=1,
                            highlightthickness=1, highlightbackground=theme.SOFT_BLUE)
        tf_code.place(x=20, y=72, width=360, height=38)

        lbl_status = tk.Label(dlg, text="", font=theme.font(11), fg=theme.RED_ACCENT,
                               bg=theme.ROOMS_BG, anchor="center")
        lbl_status.place(x=20, y=118, width=360, height=18)

        def do_join():
            code = tf_code.get().strip().upper()
            if not code:
                lbl_status.configure(text="Please enter a code.")
                return
            self._do_join_room(code, dlg, lbl_status)

        btn_ok = self._dialog_button(dlg, "Join Room", theme.GREEN_BTN, do_join)
        btn_ok.place(x=100, y=142, width=200, height=40)
        tf_code.bind("<Return>", lambda e: do_join())

        btn_cancel = self._ghost_button(dlg, "Cancel", dlg.destroy)
        btn_cancel.place(x=140, y=190, width=120, height=26)

    # ── LEAVE DEPARTMENT DIALOG (admin only) ──
    def show_leave_department_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Leave a Department")
        dlg.geometry("460x340")
        dlg.transient(self)
        dlg.grab_set()
        dlg.configure(bg=theme.ROOMS_BG)
        dlg.resizable(False, False)

        tk.Label(dlg, text="Your Departments", font=theme.font(16, "bold"), fg="white",
                 bg=theme.ROOMS_BG, anchor="w").place(x=20, y=15, width=420, height=26)
        tk.Label(dlg, text="Leaving a department removes its rooms from your lobby.",
                 font=theme.font(10, slant="italic"), fg=theme.SOFT_BLUE, bg=theme.ROOMS_BG,
                 anchor="w").place(x=20, y=43, width=420, height=16)

        list_panel = tk.Frame(dlg, bg="#1c2a55", highlightthickness=1,
                               highlightbackground=theme.MEDIUM_BLUE)
        list_panel.place(x=20, y=70, width=420, height=200)

        def load():
            for w in list_panel.winfo_children():
                w.destroy()
            try:
                conn = get_connection()
                cur = conn.cursor(dictionary=True)
                cur.execute(
                    """
                    SELECT ad.department_id, MAX(r.department_name) AS dname,
                           COUNT(r.room_id) AS n
                    FROM admin_departments ad
                    LEFT JOIN rooms r ON r.department_id = ad.department_id
                    WHERE ad.user_id = %s
                    GROUP BY ad.department_id
                    ORDER BY ad.department_id
                    """,
                    (self.current_user_id,),
                )
                rows = cur.fetchall()
                cur.close()
            except Exception as ex:
                tk.Label(list_panel, text=f"DB Error: {ex}", font=theme.font(10),
                         fg=theme.RED_ACCENT, bg="#1c2a55", wraplength=390).pack(pady=20)
                return

            if not rows:
                tk.Label(list_panel, text="You haven't joined any departments.",
                         font=theme.font(12, slant="italic"), fg="#78a0c8",
                         bg="#1c2a55").pack(pady=70)
                return

            for r in rows:
                dept_id = r["department_id"]
                name = r["dname"] or dept_id
                row_f = tk.Frame(list_panel, bg="#1c2a55", height=40)
                row_f.pack(fill="x")
                row_f.pack_propagate(False)

                tk.Label(row_f, text=f'{name}  ({dept_id})  \u2014  {r["n"]} room(s)',
                         font=theme.font(11), fg="white", bg="#1c2a55",
                         anchor="w").place(x=10, y=10, width=300, height=20)

                def make_leave(d=dept_id, n=name):
                    def _leave():
                        if not messagebox.askyesno(
                                "Leave Department",
                                f'Leave "{n}" ({d})?\nIts rooms will no longer appear in your lobby.',
                                parent=dlg):
                            return
                        try:
                            c = get_connection()
                            cu = c.cursor()
                            cu.execute(
                                "DELETE FROM admin_departments WHERE user_id=%s AND department_id=%s",
                                (self.current_user_id, d),
                            )
                            cu.close()
                            load()
                            self.refresh_rooms()
                        except Exception as ex:
                            messagebox.showerror("Error", str(ex), parent=dlg)
                    return _leave

                tk.Button(row_f, text="Leave", font=theme.font(10, "bold"), fg="white",
                          bg=theme.RED_ACCENT, relief="flat", bd=0, cursor="hand2",
                          command=make_leave()).place(x=340, y=8, width=68, height=24)

        load()

        self._ghost_button(dlg, "Close", dlg.destroy).place(x=170, y=290, width=120, height=28)

    def _do_join_room(self, code, dlg, lbl_status):
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT room_id, room_name, host_id, is_archived FROM rooms WHERE invite_code=%s",
                (code,),
            )
            room = cur.fetchone()
            if not room:
                lbl_status.configure(text="Invalid code. Please try again.")
                cur.close()
                return
            if room["is_archived"] and self.current_role != "admin":
                lbl_status.configure(text="This room has been archived.")
                cur.close()
                return
            room_id, room_name, host_id = room["room_id"], room["room_name"], room["host_id"]

            cur.execute(
                "SELECT room_role FROM room_members WHERE room_id=%s AND user_id=%s",
                (room_id, self.current_user_id),
            )
            existing = cur.fetchone()
            if existing:
                cur.close()
                dlg.destroy()
                role = existing["room_role"]
                self.enter_room(room_id, room_name, role, host_id)
                return

            cur.execute(
                "INSERT INTO room_members (room_id, user_id, room_role) VALUES (%s, %s, 'member')",
                (room_id, self.current_user_id),
            )
            cur.close()

            dlg.destroy()
            self.refresh_rooms()
            role = "member"
            self.enter_room(room_id, room_name, role, host_id)

        except Exception as ex:
            lbl_status.configure(text=f"DB Error: {ex}")

    # ── Professor: new private message previews ──
    def _count_unread_dms(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM room_messages WHERE is_private=1 "
                    "AND receiver_id=%s AND receiver_read=0", (self.current_user_id,))
        n = cur.fetchone()[0]
        cur.close()
        return n

    def _poll_notifications(self):
        try:
            n = self._count_unread_dms()
            self.btn_notify.configure(text=f"\u2709 Messages ({n})" if n else "\u2709 Messages",
                                      bg=theme.RED_ACCENT if n else "#28376e")
        except Exception as ex:
            print(f"notify poll error: {ex}")
        self.after(3000, self._poll_notifications)

    def _show_dm_previews(self):
        dlg = tk.Toplevel(self)
        dlg.title("New Private Messages")
        dlg.geometry("460x360")
        dlg.transient(self)
        dlg.grab_set()
        dlg.configure(bg=theme.ROOMS_BG)
        dlg.resizable(False, False)

        tk.Label(dlg, text="New private messages", font=theme.font(16, "bold"), fg="white",
                 bg=theme.ROOMS_BG, anchor="w").place(x=20, y=15, width=420, height=26)

        panel = tk.Frame(dlg, bg="#1c2a55", highlightthickness=1,
                         highlightbackground=theme.MEDIUM_BLUE)
        panel.place(x=20, y=55, width=420, height=250)

        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                                SELECT r.room_id, r.room_name, r.host_id, sr.sub_room_id, u.full_name, u.username,
                       COUNT(*) AS n, MAX(m.sent_at) AS last_at,
                       COALESCE(rm.room_role, 'member') AS room_role
                FROM room_messages m
                JOIN room_sub_rooms sr ON sr.sub_room_id = m.sub_room_id
                JOIN rooms r ON r.room_id = sr.room_id
                JOIN users u ON u.user_id = m.sender_id
                LEFT JOIN room_members rm ON rm.room_id = r.room_id AND rm.user_id = %s
                WHERE m.is_private = 1 AND m.receiver_id = %s AND m.receiver_read = 0
                                GROUP BY r.room_id, r.room_name, r.host_id, sr.sub_room_id, u.user_id, u.full_name,
                         u.username, rm.room_role
                ORDER BY last_at DESC
                """,
                (self.current_user_id, self.current_user_id),
            )
            rows = cur.fetchall()
            cur.close()
        except Exception as ex:
            tk.Label(panel, text=f"DB Error: {ex}", fg=theme.RED_ACCENT, bg="#1c2a55",
                     wraplength=390).pack(pady=20)
            rows = []

        if not rows:
            tk.Label(panel, text="No new private messages.", font=theme.font(12, slant="italic"),
                     fg="#78a0c8", bg="#1c2a55").pack(pady=90)

        for r in rows:
            row_f = tk.Frame(panel, bg="#1c2a55", height=48)
            row_f.pack(fill="x")
            row_f.pack_propagate(False)
            who = r["full_name"] or r["username"]
            tk.Label(row_f, text=who, font=theme.font(11, "bold"), fg="white", bg="#1c2a55",
                     anchor="w").place(x=10, y=5, width=300, height=18)
            tk.Label(row_f, text=f'{r["room_name"]}  \u00b7  {r["n"]} new', font=theme.font(10),
                     fg=theme.SOFT_BLUE, bg="#1c2a55", anchor="w").place(x=10, y=24, width=300, height=16)

            def make_open(rr=r):
                def _open():
                    dlg.destroy()
                    self.enter_room(rr["room_id"], rr["room_name"], rr["room_role"],
                                    rr["host_id"], rr["sub_room_id"])
                return _open

            tk.Button(row_f, text="Open", font=theme.font(10, "bold"), fg="white",
                      bg=theme.MEDIUM_BLUE, relief="flat", bd=0, cursor="hand2",
                      command=make_open()).place(x=340, y=10, width=68, height=26)

        self._ghost_button(dlg, "Close", dlg.destroy).place(x=170, y=318, width=120, height=28)

    # ── Archived rooms (host / admin) ──
    def _fetch_archived_rooms(self):
        """Archived rooms this user may restore: rooms they host, plus (admins)
        rooms they belong to or that are in their departments."""
        uid = self.current_user_id
        is_admin = 1 if self.current_role == "admin" else 0
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT r.room_id, r.room_name, r.host_id, r.archived_at,
                   COALESCE(rm.room_role, 'member') AS room_role
            FROM rooms r
            LEFT JOIN room_members rm ON rm.room_id = r.room_id AND rm.user_id = %s
            WHERE r.is_archived = 1
              AND (r.host_id = %s
                   OR (%s = 1 AND (rm.user_id IS NOT NULL
                        OR r.department_id IN (
                            SELECT department_id FROM admin_departments WHERE user_id = %s))))
            ORDER BY r.archived_at DESC
            """,
            (uid, uid, is_admin, uid),
        )
        rows = cur.fetchall()
        cur.close()
        return rows

    def show_archived_rooms_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Archived Rooms")
        dlg.geometry("500x420")
        dlg.transient(self)
        dlg.grab_set()
        dlg.configure(bg=theme.ROOMS_BG)
        dlg.resizable(False, False)

        tk.Label(dlg, text="Archived Rooms", font=theme.font(16, "bold"), fg="white",
                 bg=theme.ROOMS_BG, anchor="w").place(x=20, y=15, width=460, height=26)
        tk.Label(dlg, text="Tick the rooms you want to restore to your dashboard.",
                 font=theme.font(10, slant="italic"), fg=theme.SOFT_BLUE, bg=theme.ROOMS_BG,
                 anchor="w").place(x=20, y=43, width=460, height=16)

        list_panel = tk.Frame(dlg, bg="#1c2a55", highlightthickness=1,
                               highlightbackground=theme.MEDIUM_BLUE)
        list_panel.place(x=20, y=70, width=460, height=250)

        lbl_status = tk.Label(dlg, text="", font=theme.font(11, "bold"), bg=theme.ROOMS_BG,
                               anchor="center")
        lbl_status.place(x=20, y=326, width=460, height=18)

        checks = []   # (room_id, BooleanVar)

        def load():
            for w in list_panel.winfo_children():
                w.destroy()
            checks.clear()
            try:
                rows = self._fetch_archived_rooms()
            except Exception as ex:
                tk.Label(list_panel, text=f"DB Error: {ex}", font=theme.font(10),
                         fg=theme.RED_ACCENT, bg="#1c2a55", wraplength=430).pack(pady=20)
                return
            if not rows:
                tk.Label(list_panel, text="No archived rooms.",
                         font=theme.font(12, slant="italic"), fg="#78a0c8",
                         bg="#1c2a55").pack(pady=90)
                return
            for r in rows:
                var = tk.BooleanVar(value=False)
                checks.append((r["room_id"], var))
                row_f = tk.Frame(list_panel, bg="#1c2a55", height=40)
                row_f.pack(fill="x")
                row_f.pack_propagate(False)
                tk.Checkbutton(row_f, variable=var, bg="#1c2a55", selectcolor="#1c2a55",
                               activebackground="#1c2a55").place(x=6, y=8, width=24, height=24)
                name = r["room_name"]
                shown = name if len(name) <= 30 else name[:29] + "\u2026"
                tk.Label(row_f, text=shown, font=theme.font(12), fg="white", bg="#1c2a55",
                         anchor="w").place(x=36, y=10, width=320, height=20)

                def make_open(rr=r):
                    def _open():
                        dlg.destroy()
                        self.enter_room(rr["room_id"], rr["room_name"],
                                        rr["room_role"], rr["host_id"])
                    return _open

                tk.Button(row_f, text="Open", font=theme.font(10, "bold"), fg="white",
                          bg=theme.MEDIUM_BLUE, relief="flat", bd=0, cursor="hand2",
                          command=make_open()).place(x=390, y=8, width=56, height=24)

        def do_restore():
            ids = [rid for rid, v in checks if v.get()]
            if not ids:
                lbl_status.configure(fg="#ff8080", text="Tick at least one room.")
                return
            is_admin = 1 if self.current_role == "admin" else 0
            try:
                conn = get_connection()
                cur = conn.cursor()
                for rid in ids:
                    cur.execute(
                        "UPDATE rooms SET is_archived=0, archived_at=NULL "
                        "WHERE room_id=%s AND (host_id=%s OR %s=1)",
                        (rid, self.current_user_id, is_admin),
                    )
                cur.close()
            except Exception as ex:
                lbl_status.configure(fg="#ff8080", text=f"Error: {ex}")
                return
            load()
            self.refresh_rooms()
            lbl_status.configure(fg="#50d250", text=f"\u2713 Restored {len(ids)} room(s).")

        theme.make_button(dlg, "Restore Selected", theme.GREEN_BTN, font_size=12,
                          command=do_restore).place(x=100, y=352, width=300, height=38)
        self._ghost_button(dlg, "Close", dlg.destroy).place(x=190, y=394, width=120, height=22)

        load()

    # ── Enter room ──
    def enter_room(self, room_id, room_name, room_role, host_id, open_sub_room_id=None):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT is_archived FROM rooms WHERE room_id=%s", (room_id,))
            row = cur.fetchone()
            cur.close()
            if row and row[0] == 1 and room_role != "host" and self.current_role != "admin":
                messagebox.showinfo("Room archived",
                                     "This room has been archived by its host.", parent=self)
                self.refresh_rooms()
                return
        except Exception as ex:
            print(f"enter_room archive check error: {ex}")

        self.withdraw()
        from ui.room_frame import RoomFrame
        RoomFrame(self.current_user_id, self.current_username, self.current_full_name,
                   self.current_role, room_id, room_name, room_role, host_id, self,
                   open_sub_room_id)

    # ── Helpers ──
    def _display_name(self):
        return self.current_full_name or self.current_username

    def _logout(self):
        self.destroy()
        from ui.login_frame import LoginFrame
        LoginFrame().mainloop()

    def _center(self):
        self.update_idletasks()
        w, h = 960, 640
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _dlg_label(self, dlg, text, x, y):
        tk.Label(dlg, text=text, font=theme.font(11, "bold"), fg="white", bg=theme.ROOMS_BG,
                 anchor="w").place(x=x, y=y, width=380, height=18)

    def _dlg_field(self, dlg, x, y, w):
        tf = tk.Entry(dlg, font=theme.font(12), bg="white", fg=theme.DARK_NAVY, relief="solid",
                      bd=1, highlightthickness=1, highlightbackground=theme.SOFT_BLUE)
        tf.place(x=x, y=y, width=w, height=32)
        return tf

    def _dialog_button(self, dlg, text, bg, command):
        return theme.make_button(dlg, text, bg, hover_bg=theme.darker(bg), font_size=13,
                                  command=command)

    def _ghost_button(self, dlg, text, command):
        btn = tk.Button(dlg, text=text, font=theme.font(11), fg=theme.SOFT_BLUE,
                         bg=theme.ROOMS_BG, relief="flat", bd=0, cursor="hand2",
                         activebackground=theme.ROOMS_BG, activeforeground="white",
                         command=command)
        return btn
