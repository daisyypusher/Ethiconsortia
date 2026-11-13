"""
ui/room_frame.py
─────────────────────────────────────────────────────────────
    • Public sub-rooms   (normal group chat)
    • Private sub-rooms  (DM, visible only to sender + recipient + admins)
    • Profanity filter   (censors bad words, 3 warnings -> ban)
    • Room settings (host/admin): permissions, sub-room CRUD, flagged log
─────────────────────────────────────────────────────────────
"""
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from db.connection import get_connection
from ui import theme, emote_picker, image_message_handler as imh
from ui.moderation_filter import (
    filter_message, record_warning, show_warning_dialog, is_banned, log_flagged,
    find_suspicious,
    count_unread_alerts, get_admin_flagged, mark_alerts_read,
    add_filtered_word, remove_filtered_word,
)

EMOTES = [
    ["\U0001F60A", "\U0001F602", "\U0001F60D", "\U0001F97A", "\U0001F60E",
     "\U0001F62D", "\U0001F624", "\U0001F914", "\U0001F605", "\U0001F973"],
    ["\U0001F44D", "\U0001F44E", "\U0001F44F", "\U0001F64C", "\U0001F91D",
     "\U0001F44B", "\U0001F926", "\U0001F937", "\U0001F4AA", "\U0001FAC2"],
    ["\u2764\uFE0F", "\U0001F494", "\U0001F525", "\u2728", "\U0001F4AF",
     "\U0001F389", "\u2B50", "\U0001F480", "\U0001FAE1", "\U0001F64F"],
    ["\U0001F4DA", "\U0001F4BB", "\U0001F4DD", "\U0001F393", "\U0001F4E2",
     "\U0001F3C6", "\u23F0", "\U0001F4CC", "\U0001F4A1", "\U0001F680"],
]

TAG_LABELS = {
    "none":         "No tag",
    "announcement": "\U0001F4E2 Announcement",
    "question":     "\u2753 Question",
    "emergency":    "\U0001F6A8 Emergency",
    "wrong_sent":   "\u26A0 Wrong sent",
    "other":        "\U0001F3F7 Other",
}
TAG_KEYS = {label: key for key, label in TAG_LABELS.items()}
TAG_COLORS = {
    "announcement": "#1e5fb4",
    "question":     "#2e8b57",
    "emergency":    "#b41414",
    "wrong_sent":   "#c86400",
    "other":        "#6482b4",
}

RESTRICTED_MSG = "You can't send messages in this sub-room."

class RoomFrame(tk.Toplevel):
    def __init__(self, user_id, username, full_name, sys_role,
                 room_id, room_name, room_role, host_id, parent_lobby,
                 open_sub_room_id=None):
        super().__init__(parent_lobby)
        self.current_user_id = user_id
        self.current_username = username
        self.current_full_name = full_name
        self.current_sys_role = sys_role
        self.room_id = room_id
        self.room_name = room_name
        self.my_room_role = room_role
        self.host_id = host_id
        self.parent_lobby = parent_lobby

        self.selected_sub_room_id = -1
        self.selected_sub_room_name = ""
        self.selected_is_private = False
        self.selected_dm_partner_id = -1
        self.selected_sub_room_type = "text"
        self._polling_job = None
        self._img_refs = []  # keep PhotoImage references alive
        self._last_msg_sig = None       # what the chat currently shows
        self._last_members_sig = None   # what the members list currently shows
        self._last_sr_sig = None        # what the sub-room sidebar currently shows
        self._last_dm_toast_id = 0      # newest DM already previewed

        self.title(f"Ethiconsortia  \u2014  {room_name}")
        self.geometry("1150x750")
        self.resizable(False, False)
        self.configure(bg=theme.DARK_NAVY)
        self.protocol("WM_DELETE_WINDOW", self.go_back)
        self._center()

        root = tk.Frame(self, bg=theme.DARK_NAVY)
        root.place(x=0, y=0, width=1150, height=750)

        server_bar = self._build_server_bar(root)
        sub_rooms_side = self._build_sub_rooms_sidebar(root)
        chat_area = self._build_chat_area(root)
        members_side = self._build_members_sidebar(root)

        server_bar.place(x=0, y=0, width=65, height=700)
        sub_rooms_side.place(x=65, y=0, width=220, height=700)
        chat_area.place(x=285, y=0, width=600, height=700)
        members_side.place(x=880, y=0, width=270, height=750)

        self.load_sub_rooms()
        if open_sub_room_id is not None:
            self.open_sub_room(open_sub_room_id)
        self.load_members()
        self.start_polling()

    # ═════════════════════════════════════════════════════════════════
    #  SERVER BAR
    # ═════════════════════════════════════════════════════════════════
    def _build_server_bar(self, parent):
        p = tk.Frame(parent, bg=theme.DARKER_NAVY)

        icon = theme.RoundedCanvas(p, width=46, height=46, bg=theme.DARKER_NAVY,
                                    highlightthickness=0)
        icon.place(x=10, y=12)
        icon.rounded_rect(0, 0, 46, 46, radius=23, fill=theme.MEDIUM_BLUE, outline="")
        icon.create_text(23, 23, text=self.room_name[0].upper(), fill="white",
                          font=theme.font(22, "bold"))

        tk.Frame(p, bg=theme.MEDIUM_BLUE, height=2).place(x=8, y=66, width=50, height=2)

        btn_back = theme.make_button(p, "\u2190 Back", "#28376e", font_size=9,
                                      bold=True, command=self.go_back)
        btn_back.place(x=5, y=600, width=55, height=36)

        btn_logout = theme.make_button(p, "Logout", theme.RED_ACCENT, font_size=9,
                                        command=self._logout)
        btn_logout.place(x=5, y=642, width=55, height=30)

        return p

    # ═════════════════════════════════════════════════════════════════
    #  SUB-ROOMS SIDEBAR
    # ═════════════════════════════════════════════════════════════════
    def _build_sub_rooms_sidebar(self, parent):
        p = tk.Frame(parent, bg=theme.SUB_ROOM_BG)

        tk.Label(p, text=self.room_name.upper(), font=theme.font(12, "bold"), fg="white",
                 bg=theme.SUB_ROOM_BG, anchor="w").place(x=12, y=14, width=168, height=22)

        is_host_or_admin = self.my_room_role == "host" or self.current_sys_role == "admin"
        if is_host_or_admin:
            cog = tk.Button(p, text="\u2699", font=theme.font(13, "bold", emoji=True),
                             fg="white", bg=theme.SUB_ROOM_BG, relief="solid", bd=1,
                             highlightbackground=theme.SOFT_BLUE, cursor="hand2",
                             command=self.open_room_settings)
            cog.place(x=185, y=10, width=26, height=26)

        tk.Frame(p, bg="#324878", height=2).place(x=0, y=46, width=220, height=2)

        tk.Label(p, text="SUB-ROOMS", font=theme.font(10, "bold"), fg="#8ca5d2",
                 bg=theme.SUB_ROOM_BG, anchor="w").place(x=12, y=55, width=196, height=16)

        sr_canvas = tk.Canvas(p, bg=theme.SUB_ROOM_BG, highlightthickness=0)
        sr_canvas.place(x=0, y=74, width=220, height=480)
        self._sr_canvas = sr_canvas
        self.sub_rooms_list_panel = tk.Frame(sr_canvas, bg=theme.SUB_ROOM_BG)
        sr_canvas.create_window((0, 0), window=self.sub_rooms_list_panel, anchor="nw", width=220)
        self.sub_rooms_list_panel.bind(
            "<Configure>", lambda e: sr_canvas.configure(scrollregion=sr_canvas.bbox("all")))

        tk.Frame(p, bg="#502882", height=2).place(x=0, y=558, width=220, height=2)
        tk.Label(p, text="DIRECT MESSAGES", font=theme.font(10, "bold"), fg="#8ca5d2",
                 bg=theme.SUB_ROOM_BG, anchor="w").place(x=12, y=562, width=196, height=16)

        btn_dm = theme.make_button(p, "\u2709  New Private Message", theme.DM_BADGE_BG,
                                    font_size=10, command=self.open_dm_picker)
        btn_dm.place(x=8, y=582, width=204, height=32)

        if self.current_sys_role in ("professor", "admin"):
            btn_fw = theme.make_button(p, "\U0001F6AB  Filtered Words", theme.WARN_ORANGE,
                                        font_size=10, emoji=True,
                                        command=self.open_filtered_words_dialog)
            btn_fw.place(x=8, y=618, width=204, height=30)

        # User info bar
        user_bar = tk.Frame(p, bg="#162248")
        user_bar.place(x=0, y=652, width=220, height=48)
        tk.Label(user_bar, text="\U0001F464", font=theme.font(17, emoji=True), fg="white",
                 bg="#162248").place(x=8, y=10, width=28, height=28)
        dn = self._display_name()
        dn_short = (dn[:16] + "\u2026") if len(dn) > 16 else dn
        tk.Label(user_bar, text=dn_short, font=theme.font(10, "bold"), fg="white",
                 bg="#162248", anchor="w").place(x=40, y=8, width=170, height=15)
        role_txt = theme.role_label(self.current_sys_role)
        if self.my_room_role == "host":
            role_txt += "  \u00b7  HOST"
        tk.Label(user_bar, text=role_txt, font=theme.font(9), fg=theme.SOFT_BLUE,
                 bg="#162248", anchor="w").place(x=40, y=25, width=170, height=13)

        return p

    def load_sub_rooms(self):
        # 1) fetch + work out what this user is allowed to see
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT s.sub_room_id, s.sub_room_name, s.sub_room_type, "
                "s.sub_room_type_detail, s.dm_user_a, s.dm_user_b, "
                "COALESCE(NULLIF(ua.full_name,''), ua.username) AS dm_a_name, "
                "COALESCE(NULLIF(ub.full_name,''), ub.username) AS dm_b_name "
                "FROM room_sub_rooms s "
                "LEFT JOIN users ua ON ua.user_id = s.dm_user_a "
                "LEFT JOIN users ub ON ub.user_id = s.dm_user_b "
                "WHERE s.room_id=%s ORDER BY s.position ASC",
                (self.room_id,),
            )
            rows = cur.fetchall()
            cur.close()
            readable = self._readable_sub_room_ids()
        except Exception as ex:
            print(f"load_sub_rooms error: {ex}")
            return

        items = []   # (sr_id, shown_name, sr_type, is_private, dm_partner_id, full_name)
        for r in rows:
            sr_id, sr_name, sr_type = r["sub_room_id"], r["sub_room_name"], r["sub_room_type"]
            is_private = r["sub_room_type_detail"] == "private"
            dm_a, dm_b = r["dm_user_a"], r["dm_user_b"]
            full_name = sr_name   # what the chat header shows
            if not is_private and readable is not None and sr_id not in readable:
                continue

            dm_partner_id = -1
            if is_private:
                is_participant = dm_a == self.current_user_id or dm_b == self.current_user_id
                if not is_participant and self.current_sys_role != "admin":
                    continue
                a_name = r["dm_a_name"] or "?"
                b_name = r["dm_b_name"] or "?"
                if is_participant:
                    partner = b_name if dm_a == self.current_user_id else a_name
                    full_name = f"DM-{partner}"
                    sr_name = full_name
                    dm_partner_id = dm_b if dm_a == self.current_user_id else dm_a
                else:
                    full_name = f"DM-{a_name} \u2194 {b_name}"
                    sr_name = f"DM-{a_name.split(' ')[0]} \u2194 {b_name.split(' ')[0]}"
                if len(sr_name) > 24:
                    sr_name = sr_name[:23] + "\u2026"

            items.append((sr_id, sr_name, sr_type, is_private, dm_partner_id, full_name))

        # 2) nothing changed -> leave the sidebar alone (no flicker, no selection reset)
        sig = tuple(items)
        if sig == self._last_sr_sig:
            return
        self._last_sr_sig = sig

        # 3) rebuild
        for w in self.sub_rooms_list_panel.winfo_children():
            w.destroy()

        last_section = ""
        for sr_id, sr_name, sr_type, is_private, dm_partner_id, full_name in items:
            section = "DM" if is_private else "PUBLIC"
            if section != last_section:
                tk.Label(
                    self.sub_rooms_list_panel,
                    text="\u2014 PRIVATE MESSAGES" if is_private else "\u2014 CHANNELS",
                    font=theme.font(10, "bold"), fg="#8ca5d2", bg=theme.SUB_ROOM_BG,
                    anchor="w").pack(fill="x", padx=10, pady=(8, 2))
                last_section = section
            self._build_sub_room_row(sr_id, sr_name, sr_type, is_private,
                                      dm_partner_id, full_name).pack(fill="x")

        # 4) only jump to the first sub-room if the current one isn't available anymore
        visible_ids = {i[0] for i in items}
        if items and self.selected_sub_room_id not in visible_ids:
            first = items[0]
            self.select_sub_room(first[0], first[5], first[3], first[4])
        elif not items:
            self.selected_sub_room_id = -1
            self.lbl_sub_room_header.configure(text="# Select a sub-room")
            for cw in self.chat_messages_panel.winfo_children():
                cw.destroy()
            self._last_msg_sig = None

    def _build_sub_room_row(self, ch_id, ch_name, ch_type, is_private, dm_partner_id,
                            full_name=None):
        row = tk.Frame(self.sub_rooms_list_panel, bg=theme.SUB_ROOM_BG, height=36, cursor="hand2")
        row.pack_propagate(False)

        icon = "\U0001F512" if is_private else ("\U0001F4E2" if ch_type == "announcement" else "\u25B8")
        icon_fg = "#be82ff" if is_private else "#a0b9e6"
        name_fg = "#c8a0ff" if is_private else "#afc6f0"

        icon_lbl = tk.Label(row, text=icon, font=theme.font(13, emoji=True), fg=icon_fg,
                             bg=theme.SUB_ROOM_BG)
        icon_lbl.place(x=10, y=7, width=22, height=22)

        name_lbl = tk.Label(row, text=ch_name, font=theme.font(12), fg=name_fg,
                             bg=theme.SUB_ROOM_BG, anchor="w")
        name_lbl.place(x=36, y=8, width=175, height=18)

        def refresh_style():
            selected = ch_id == self.selected_sub_room_id
            bg = ("#5a1e8c" if is_private else "#324e94") if selected else theme.SUB_ROOM_BG
            row.configure(bg=bg)
            icon_lbl.configure(bg=bg)
            name_lbl.configure(bg=bg, fg="white" if selected else name_fg)

        row._refresh_style = refresh_style
        refresh_style()

        def on_click(_e=None):
            self.select_sub_room(ch_id, full_name or ch_name, is_private, dm_partner_id)

        for w in (row, icon_lbl, name_lbl):
            w.bind("<Button-1>", on_click)
            w.bind("<Enter>", lambda e: name_lbl.configure(fg="white"))
            w.bind("<Leave>", lambda e: refresh_style())

        return row

    def select_sub_room(self, ch_id, ch_name, is_private, dm_partner_id):
        self.selected_sub_room_id = ch_id
        self.selected_sub_room_name = ch_name
        self.selected_is_private = is_private
        self.selected_dm_partner_id = dm_partner_id

        self.selected_sub_room_type = "text"
        if not is_private:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("SELECT sub_room_type FROM room_sub_rooms WHERE sub_room_id=%s",
                            (ch_id,))
                row = cur.fetchone()
                cur.close()
                if row:
                    self.selected_sub_room_type = row[0]
            except Exception as ex:
                print(f"select_sub_room type lookup error: {ex}")

        prefix = "\U0001F512 " if is_private else "\u25B8 "
        suffix = "  [Private]" if is_private else ""
        self.lbl_sub_room_header.configure(text=f"{prefix}{ch_name}{suffix}",
                                            fg=theme.DM_COLOR if is_private else theme.DARK_NAVY)

        self.refresh_messages()
        self.apply_permissions_to_input()
        for w in self.sub_rooms_list_panel.winfo_children():
            if hasattr(w, "_refresh_style"):
                w._refresh_style()

    def open_sub_room(self, sr_id):
        """Jumps straight to one sub-room (used by notification Open buttons).
        select_sub_room scrolls to the newest message."""
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT s.sub_room_name, s.sub_room_type_detail, s.dm_user_a, s.dm_user_b, "
                "COALESCE(NULLIF(ua.full_name,''), ua.username) AS dm_a_name, "
                "COALESCE(NULLIF(ub.full_name,''), ub.username) AS dm_b_name "
                "FROM room_sub_rooms s "
                "LEFT JOIN users ua ON ua.user_id = s.dm_user_a "
                "LEFT JOIN users ub ON ub.user_id = s.dm_user_b "
                "WHERE s.sub_room_id=%s AND s.room_id=%s",
                (sr_id, self.room_id),
            )
            r = cur.fetchone()
            cur.close()
        except Exception as ex:
            print(f"open_sub_room error: {ex}")
            return
        if not r:
            return

        is_private = r["sub_room_type_detail"] == "private"
        name, partner = r["sub_room_name"], -1
        if is_private:
            a, b = r["dm_user_a"], r["dm_user_b"]
            a_name, b_name = r["dm_a_name"] or "?", r["dm_b_name"] or "?"
            if self.current_user_id in (a, b):
                partner = b if a == self.current_user_id else a
                name = f"DM-{b_name if a == self.current_user_id else a_name}"
            elif self.current_sys_role == "admin":
                name = f"DM-{a_name} \u2194 {b_name}"
            else:
                return          # DMs are only for the two people in them and admins
        self.select_sub_room(sr_id, name, is_private, partner)

    # ═════════════════════════════════════════════════════════════════
    #  DM PICKER
    # ═════════════════════════════════════════════════════════════════
    def open_dm_picker(self):
        dlg = tk.Toplevel(self)
        dlg.title("Start Private Conversation")
        dlg.geometry("360x460")
        dlg.transient(self)
        dlg.grab_set()
        dlg.configure(bg=theme.SUB_ROOM_BG)
        dlg.resizable(False, False)

        tk.Label(dlg, text="Select a room member to message privately",
                 font=theme.font(12, "bold"), fg="white", bg=theme.SUB_ROOM_BG,
                 anchor="w").place(x=14, y=14, width=330, height=20)
        tk.Label(dlg, text="Only you, them, and admins can see this conversation.",
                 font=theme.font(10, slant="italic"), fg="#beaaff", bg=theme.SUB_ROOM_BG,
                 anchor="w").place(x=14, y=36, width=330, height=16)
        tk.Frame(dlg, bg=theme.MEDIUM_BLUE, height=2).place(x=0, y=58, width=360, height=2)

        member_map = {}
        listbox = tk.Listbox(dlg, bg="#1c2a55", fg="white", font=theme.font(12),
                              selectbackground=theme.DM_BADGE_BG, height=15,
                              highlightthickness=1, highlightbackground=theme.MEDIUM_BLUE)
        listbox.place(x=14, y=68, width=330, height=300)

        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT u.user_id, u.full_name, u.username
                FROM room_members rm
                JOIN users u ON rm.user_id = u.user_id
                WHERE rm.room_id = %s AND rm.user_id != %s
                ORDER BY u.full_name ASC
                """,
                (self.room_id, self.current_user_id),
            )
            for r in cur.fetchall():
                fn = r["full_name"] or r["username"]
                display = f'{fn} (@{r["username"]})'
                member_map[display] = r["user_id"]
                listbox.insert(tk.END, display)
            cur.close()
        except Exception as ex:
            messagebox.showerror("Error", f"Error loading members: {ex}", parent=self)
            dlg.destroy()
            return

        def start_chat():
            sel = listbox.curselection()
            if not sel:
                messagebox.showinfo("Info", "Please select a member first.", parent=dlg)
                return
            display = listbox.get(sel[0])
            partner_id = member_map[display]
            dlg.destroy()
            self.open_or_create_dm_sub_room(partner_id, display)

        btn_start = theme.make_button(dlg, "Start Private Chat", theme.DM_BADGE_BG,
                                       font_size=12, command=start_chat)
        btn_start.place(x=80, y=382, width=200, height=36)

    def open_or_create_dm_sub_room(self, partner_id, partner_display):
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)

            dm_a, dm_b = min(self.current_user_id, partner_id), max(self.current_user_id, partner_id)

            cur.execute(
                "SELECT sub_room_id, sub_room_name FROM room_sub_rooms "
                "WHERE room_id=%s AND sub_room_type_detail='private' AND dm_user_a=%s AND dm_user_b=%s",
                (self.room_id, dm_a, dm_b),
            )
            existing = cur.fetchone()

            import re
            stripped = re.sub(r"\s*\(@.*?\)", "", partner_display).strip()

            if existing:
                sr_id = existing["sub_room_id"]
            else:
                sr_name = f"DM-{dm_a}-{dm_b}"   # internal name only; the label is built on display

                cur.execute(
                    "SELECT COALESCE(MAX(position)+1, 0) AS p FROM room_sub_rooms WHERE room_id=%s",
                    (self.room_id,),
                )
                pos = cur.fetchone()["p"]

                cur2 = conn.cursor()
                cur2.execute(
                    "INSERT INTO room_sub_rooms "
                    "(room_id, sub_room_name, sub_room_type, sub_room_type_detail, position, "
                    "dm_user_a, dm_user_b) VALUES (%s, %s, 'text', 'private', %s, %s, %s)",
                    (self.room_id, sr_name, pos, dm_a, dm_b),
                )
                sr_id = cur2.lastrowid
                cur2.close()
            cur.close()

            self.load_sub_rooms()
            self.select_sub_room(sr_id, f"DM-{stripped}", True, partner_id)

        except Exception as ex:
            messagebox.showerror("Error", f"Error opening DM: {ex}", parent=self)

    # ═════════════════════════════════════════════════════════════════
    #  CHAT AREA
    # ═════════════════════════════════════════════════════════════════
    def _build_chat_area(self, parent):
        p = tk.Frame(parent, bg=theme.CHAT_BG)

        hdr = tk.Frame(p, bg="#d2deF5")
        hdr.place(x=0, y=0, width=600, height=50)
        self.lbl_sub_room_header = tk.Label(hdr, text="# Select a sub-room",
                                             font=theme.font(15, "bold"), fg=theme.DARK_NAVY,
                                             bg="#d2deF5", anchor="w")
        self.lbl_sub_room_header.place(x=14, y=12, width=420, height=24)

        self.btn_alerts = tk.Button(hdr, text="", font=theme.font(10, "bold"), fg="white",
                                     bg=theme.RED_ACCENT, relief="flat", bd=0, cursor="hand2",
                                     command=lambda: self.open_flagged_messages_viewer(self))

        msg_canvas = tk.Canvas(p, bg=theme.CHAT_BG, highlightthickness=0)
        msg_scroll = tk.Scrollbar(p, orient="vertical", command=msg_canvas.yview)
        msg_canvas.configure(yscrollcommand=msg_scroll.set)
        msg_canvas.place(x=0, y=50, width=584, height=586)
        msg_scroll.place(x=584, y=50, width=16, height=586)

        self.chat_messages_panel = tk.Frame(msg_canvas, bg=theme.CHAT_BG)
        self._chat_window = msg_canvas.create_window((0, 0), window=self.chat_messages_panel,
                                                       anchor="nw", width=584)
        # scroll area is never shorter than the visible chat area -> no blank scrolling
        self.chat_messages_panel.bind(
            "<Configure>",
            lambda e: msg_canvas.configure(
                scrollregion=(0, 0, 584, max(e.height, msg_canvas.winfo_height()))))
        self._msg_canvas = msg_canvas

        # mouse wheel (Windows/macOS use <MouseWheel>, Linux uses Button-4/5)
        self.bind("<MouseWheel>", self._on_mousewheel, add="+")
        self.bind("<Button-4>", self._on_mousewheel, add="+")
        self.bind("<Button-5>", self._on_mousewheel, add="+")

        # Input bar
        input_bar = tk.Frame(p, bg=theme.INPUT_BG)
        input_bar.place(x=0, y=636, width=600, height=64)

        btn_image = self._make_input_icon_button(input_bar, "\U0001F4C1", "Send Image")
        btn_image.place(x=8, y=14, width=42, height=36)
        btn_image.configure(command=self.open_image_chooser)

        btn_emoji = self._make_input_icon_button(input_bar, "\u263A", "Emotes")
        btn_emoji.place(x=55, y=14, width=42, height=36)
        btn_emoji.configure(command=lambda: emote_picker.show(btn_emoji, self.send_emote))

        self.txt_message = tk.Entry(input_bar, font=theme.font(12), fg="gray", bg="white",
                                     relief="solid", bd=1, highlightthickness=1,
                                     highlightbackground=theme.SOFT_BLUE)
        self.txt_message.insert(0, "Type a message...")
        self.txt_message.place(x=102, y=14, width=308, height=36)

        self.cmb_tag = ttk.Combobox(input_bar, values=list(TAG_LABELS.values()),
                                     state="readonly", font=theme.font(9))
        self.cmb_tag.set(TAG_LABELS["none"])
        self.cmb_tag.place(x=416, y=14, width=98, height=36)
        self.cmb_tag.bind("<<ComboboxSelected>>", self._on_tag_change)

        # Required label box, only shown when "Other" is selected
        self.txt_tag_label = theme.placeholder_entry(input_bar, "Label (required)",
                                                      font_obj=theme.font(10))

        def on_focus_in(_e):
            if self.txt_message.get() == "Type a message...":
                self.txt_message.delete(0, tk.END)
                self.txt_message.configure(fg=theme.DARK_NAVY)

        def on_focus_out(_e):
            if not self.txt_message.get():
                self.txt_message.insert(0, "Type a message...")
                self.txt_message.configure(fg="gray")

        self.txt_message.bind("<FocusIn>", on_focus_in)
        self.txt_message.bind("<FocusOut>", on_focus_out)
        self.txt_message.bind("<Return>", lambda e: self.send_message())

        self.btn_send = theme.make_button(input_bar, "Send", theme.DARK_NAVY, font_size=14,
                                           command=self.send_message)
        self.btn_send.place(x=520, y=14, width=68, height=36)

        return p

    def _make_input_icon_button(self, parent, icon, tooltip):
        btn = tk.Button(parent, text=icon, font=theme.font(18, "bold", emoji=True),
                         fg=theme.DARK_NAVY, bg=theme.INPUT_BG, relief="flat", bd=0,
                         activebackground="#c8d7f5", cursor="hand2")
        theme.add_hover(btn, theme.INPUT_BG, "#c8d7f5")
        return btn

    def send_emote(self, emote):
        if self.selected_sub_room_id == -1:
            messagebox.showinfo("Info", "Please select a sub-room first.", parent=self)
            return
        if not self._check_can_post():
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            receiver_id = self.selected_dm_partner_id if (self.selected_is_private and
                                                            self.selected_dm_partner_id != -1) else None
            cur.execute(
                "INSERT INTO room_messages (sub_room_id, sender_id, content, msg_type, "
                "is_private, receiver_id) VALUES (%s,%s,%s,'emote',%s,%s)",
                (self.selected_sub_room_id, self.current_user_id, emote,
                 1 if self.selected_is_private else 0, receiver_id),
            )
            cur.close()
            self.refresh_messages()
        except Exception as ex:
            messagebox.showerror("Error", f"Error sending emote: {ex}", parent=self)

    def open_image_chooser(self):
        if self.selected_sub_room_id == -1:
            messagebox.showinfo("Info", "Please select a sub-room first.", parent=self)
            return
        if not self._check_can_post(upload=True):
            return
        path = imh.choose_attachment(self)
        if not path:
            return
        try:
            mime = imh.guess_mime_any(path)
            if mime.startswith("image/"):
                msg_type = "image"
                stored = f"{mime}|{imh.file_to_base64_raw(path)}"
            else:
                msg_type = "video" if mime.startswith("video/") else "file"
                stored = imh.encode_attachment(path)

            conn = get_connection()
            cur = conn.cursor()
            receiver_id = self.selected_dm_partner_id if (self.selected_is_private and
                                                            self.selected_dm_partner_id != -1) else None
            cur.execute(
                "INSERT INTO room_messages (sub_room_id, sender_id, content, msg_type, "
                "is_private, receiver_id) VALUES (%s,%s,%s,%s,%s,%s)",
                (self.selected_sub_room_id, self.current_user_id, stored, msg_type,
                 1 if self.selected_is_private else 0, receiver_id),
            )
            cur.close()
            self.refresh_messages()
        except Exception as ex:
            messagebox.showerror("Error", f"Error sending file: {ex}", parent=self)

    # ═════════════════════════════════════════════════════════════════
    #  MEMBERS SIDEBAR
    # ═════════════════════════════════════════════════════════════════
    def _build_members_sidebar(self, parent):
        p = tk.Frame(parent, bg=theme.RIGHT_BG)

        tk.Label(p, text="MEMBERS", font=theme.font(11, "bold"), fg="#6482b4", bg=theme.RIGHT_BG,
                 anchor="w").place(x=12, y=14, width=265, height=18)
        if self.current_sys_role == "admin":
            btn_host = theme.make_button(p, "Assign Host", theme.MEDIUM_BLUE, font_size=9,
                                          command=self.open_assign_host_dialog)
            btn_host.place(x=175, y=10, width=85, height=24)
        tk.Frame(p, bg=theme.SOFT_BLUE, height=2).place(x=0, y=38, width=265, height=2)

        canvas = tk.Canvas(p, bg=theme.RIGHT_BG, highlightthickness=0)
        canvas.place(x=0, y=42, width=265, height=580)
        self._members_canvas = canvas
        self.members_list_panel = tk.Frame(canvas, bg=theme.RIGHT_BG)
        canvas.create_window((0, 0), window=self.members_list_panel, anchor="nw", width=265)
        self.members_list_panel.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        return p

    def load_members(self):
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT u.user_id, u.full_name, u.username,
                       u.role AS sys_role, rm.room_role,
                       (SELECT GROUP_CONCAT(rr.role_name ORDER BY rr.role_name SEPARATOR ', ')
                          FROM room_member_roles mr
                          JOIN room_roles rr ON rr.role_id = mr.role_id
                         WHERE mr.user_id = u.user_id AND mr.room_id = %s) AS role_names,
                       COALESCE(uw.is_banned, 0) AS is_banned
                FROM room_members rm
                JOIN users u ON rm.user_id = u.user_id
                LEFT JOIN user_warnings uw ON uw.user_id = u.user_id
                WHERE rm.room_id = %s
                ORDER BY
                    FIELD(rm.room_role,'host','member'),
                    FIELD(u.role,'admin','professor','student'),
                    u.full_name ASC
                """,
                (self.room_id, self.room_id),
            )
            rows = cur.fetchall()
            cur.close()
        except Exception as ex:
            print(f"load_members error: {ex}")
            return

        # nothing changed -> leave the list alone
        # (my own manage-members permission is included because it decides who gets a kick button)
        sig = (tuple(tuple(r.items()) for r in rows),
               self.get_permission("can_manage_members"))
        if sig == self._last_members_sig:
            return
        self._last_members_sig = sig

        for w in self.members_list_panel.winfo_children():
            w.destroy()

        last_section = ""
        for r in rows:
            sys_role, member_role = r["sys_role"], r["room_role"]
            is_banned_u = r["is_banned"] == 1

            section = ("HOST" if member_role == "host" else
                       "ADMINISTRATORS" if sys_role == "admin" else
                       "PROFESSORS" if sys_role == "professor" else "STUDENTS")

            if section != last_section:
                self._build_section_header(section).pack(fill="x")
                last_section = section

            self._build_member_row(r["user_id"], r["full_name"], r["username"],
                                    sys_role, member_role, is_banned_u,
                                    r["role_names"]).pack(fill="x")

    def _build_section_header(self, text):
        return tk.Label(self.members_list_panel, text=text, font=theme.font(10, "bold"),
                         fg="#6482b4", bg=theme.RIGHT_BG, anchor="center", pady=6)

    def _build_member_row(self, uid, fn, un, sys_role, member_role, is_banned_u, role_names=None):
        row = tk.Frame(self.members_list_panel, bg=(
            "#d2e1f5" if uid == self.current_user_id else theme.RIGHT_BG), height=40)
        row.pack_propagate(False)

        dot = "\u26d4" if is_banned_u else "\u25cf"
        tk.Label(row, text=dot, font=theme.font(10, emoji=True),
                 fg=theme.RED_ACCENT if is_banned_u else theme.GREEN_ON,
                 bg=row["bg"]).place(x=6, y=14, width=16, height=12)

        emoji = {"professor": "\U0001F468\u200D\U0001F3EB", "admin": "\U0001F6E1"}.get(sys_role, "\U0001F464")
        tk.Label(row, text=emoji, font=theme.font(14, emoji=True), bg=row["bg"]).place(
            x=22, y=8, width=24, height=24)

        dname = fn or un
        if len(dname) > 18:
            dname = dname[:18] + "\u2026"
        is_me = uid == self.current_user_id
        name_text = dname + ("  (you)" if is_me else "") + ("  \U0001F6AB" if is_banned_u else "")
        name_fg = theme.RED_ACCENT if is_banned_u else ("#28a050" if is_me else theme.DARK_NAVY)
        tk.Label(row, text=name_text, font=theme.font(10, "bold"), fg=name_fg, bg=row["bg"],
                 anchor="w").place(x=50, y=6, width=160, height=15)

        sub = f"HOST \u00b7 {theme.role_label(sys_role)}" if member_role == "host" else theme.role_label(sys_role)
        if role_names and member_role != "host":
            sub += "  \u00b7  " + role_names[:20]
        tk.Label(row, text=sub, font=theme.font(9), fg=(theme.RED_ACCENT if member_role == "host"
                 else "#6482b4"), bg=row["bg"], anchor="w").place(x=50, y=22, width=160, height=13)

        is_admin_viewer = self.current_sys_role == "admin"
        can_kick = is_admin_viewer or (
            self.get_permission("can_manage_members")
            and member_role != "host"
            and sys_role != "admin"
        )
        if can_kick and uid != self.current_user_id:
            kick = tk.Button(row, text="X", font=theme.font(9, "bold"), fg="white",
                            bg=theme.RED_ACCENT, relief="flat", bd=0, cursor="hand2",
                            command=lambda: self.kick_member(uid, dname))
            kick.place(x=225, y=10, width=28, height=22)

        if self.current_sys_role == "admin" and is_banned_u:
            unban = tk.Button(row, text="\u21a9", font=theme.font(9, "bold"), fg="white",
                               bg="#288c50", relief="flat", bd=0, cursor="hand2",
                               command=lambda: self.unban_user(uid, dname))
            unban.place(x=204, y=10, width=22, height=22)

        return row

    def kick_member(self, uid, name):
        if uid == self.current_user_id:
            return

        # Must hold the manage-members permission (admins always do)
        if not self.get_permission("can_manage_members"):
            messagebox.showwarning("Not allowed",
                                    "You don't have permission to remove members.",
                                    parent=self)
            return

        # Look up the target fresh from the DB, not from what the screen shows
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT rm.room_role, u.role AS sys_role FROM room_members rm "
                "JOIN users u ON u.user_id = rm.user_id "
                "WHERE rm.room_id=%s AND rm.user_id=%s",
                (self.room_id, uid),
            )
            row = cur.fetchone()
            cur.close()
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)
            return

        if not row:                      # already gone, just refresh the list
            self.load_members()
            return

        was_host = row["room_role"] == "host"

        if self.current_sys_role != "admin":
            if was_host:
                messagebox.showwarning("Not allowed",
                                        "Only an administrator can remove the host.",
                                        parent=self)
                return
            if row["sys_role"] == "admin":
                messagebox.showwarning("Not allowed",
                                        "Administrators can't be removed from a room.",
                                        parent=self)
                return

        if not messagebox.askyesno("Remove Member", f'Remove "{name}" from this room?',
                                    parent=self):
            return

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM room_members WHERE room_id=%s AND user_id=%s",
                        (self.room_id, uid))
            if was_host:
                cur.execute("UPDATE rooms SET host_id=NULL WHERE room_id=%s", (self.room_id,))
                self.host_id = None
            cur.close()
            self.load_members()

            if was_host:
                messagebox.showinfo("Host removed",
                                     "This room has no host now.\nPlease assign a new host.",
                                     parent=self)
                self.open_assign_host_dialog()
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)

    def open_assign_host_dialog(self):
        if self.current_sys_role != "admin":
            return
        dlg = tk.Toplevel(self)
        dlg.title("Assign Host")
        dlg.geometry("360x420")
        dlg.transient(self)
        dlg.grab_set()
        dlg.configure(bg=theme.SUB_ROOM_BG)
        dlg.resizable(False, False)

        tk.Label(dlg, text="Select the new host", font=theme.font(12, "bold"), fg="white",
                 bg=theme.SUB_ROOM_BG, anchor="w").place(x=14, y=14, width=330, height=20)

        member_map = {}
        lb = tk.Listbox(dlg, bg="#1c2a55", fg="white", font=theme.font(12),
                         selectbackground=theme.MEDIUM_BLUE, exportselection=False,
                         highlightthickness=1, highlightbackground=theme.MEDIUM_BLUE)
        lb.place(x=14, y=44, width=330, height=280)

        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT u.user_id, u.full_name, u.username
                FROM room_members rm JOIN users u ON u.user_id = rm.user_id
                WHERE rm.room_id = %s AND u.role != 'admin'
                ORDER BY u.full_name ASC
                """,
                (self.room_id,),
            )
            for r in cur.fetchall():
                label = f'{r["full_name"] or r["username"]} (@{r["username"]})'
                member_map[label] = r["user_id"]
                lb.insert(tk.END, label)
            cur.close()
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=dlg)
            dlg.destroy()
            return

        def do_assign():
            sel = lb.curselection()
            if not sel:
                messagebox.showinfo("Info", "Please select a member.", parent=dlg)
                return
            new_id = member_map[lb.get(sel[0])]
            try:
                conn = get_connection()
                cur = conn.cursor()
                # demote any existing host, then promote the new one with full permissions
                cur.execute("UPDATE room_members SET room_role='member' "
                            "WHERE room_id=%s AND room_role='host'", (self.room_id,))
                cur.execute(
                    "UPDATE room_members SET room_role='host', can_send_messages=1, "
                    "can_read_history=1, can_manage_members=1 "
                    "WHERE room_id=%s AND user_id=%s", (self.room_id, new_id))
                cur.execute("UPDATE rooms SET host_id=%s WHERE room_id=%s", (new_id, self.room_id))
                cur.close()
                self.host_id = new_id
                dlg.destroy()
                self.load_members()
            except Exception as ex:
                messagebox.showerror("Error", str(ex), parent=dlg)

        btn = theme.make_button(dlg, "Assign as Host", theme.MEDIUM_BLUE, font_size=12,
                                 command=do_assign)
        btn.place(x=80, y=340, width=200, height=38)

    def unban_user(self, uid, name):
        if not messagebox.askyesno("Unban User", f'Unban "{name}" and reset their warnings?',
                                    parent=self):
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE user_warnings SET is_banned=0, warn_count=0 WHERE user_id=%s", (uid,))
            cur.execute("UPDATE users SET is_banned=0 WHERE user_id=%s", (uid,))
            cur.close()
            messagebox.showinfo("Unbanned", f"{name} has been unbanned and warnings reset.",
                                 parent=self)
            self.load_members()
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)

    # ═════════════════════════════════════════════════════════════════
    #  MESSAGES — REFRESH
    # ═════════════════════════════════════════════════════════════════
    def refresh_messages(self):
        if self.selected_sub_room_id == -1:
            return

        if not self.selected_is_private and self.current_sys_role != "admin":
            if not self.channel_perms(self.selected_sub_room_id)[0]:
                if self._last_msg_sig != "no-permission":
                    self.show_no_permission(
                        "\U0001F512  You don't have permission to read messages here.")
                    self._last_msg_sig = "no-permission"
                return

        # 1) fetch first
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT u.user_id, u.username, u.full_name, u.role AS sys_role,
                       m.message_id, m.sender_id, m.is_edited, m.msg_tag, m.msg_tag_label,
                       m.content, m.sent_at, m.is_private,
                       COALESCE(m.msg_type, 'text') AS msg_type
                FROM room_messages m
                JOIN users u ON m.sender_id = u.user_id
                WHERE m.sub_room_id = %s
                ORDER BY m.sent_at ASC
                """,
                (self.selected_sub_room_id,),
            )
            rows = cur.fetchall()
            cur.close()
            if self.selected_is_private:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE room_messages SET receiver_read=1 WHERE sub_room_id=%s "
                    "AND receiver_id=%s AND receiver_read=0",
                    (self.selected_sub_room_id, self.current_user_id))
                cur.close()
        except Exception as ex:
            print(f"refresh_messages error: {ex}")
            return

        # 2) nothing changed -> don't touch the screen
        sig = (self.selected_sub_room_id,
               tuple((r["message_id"], r["is_edited"], r["msg_tag"], r["msg_tag_label"],
                      hash(r["content"])) for r in rows))
        if sig == self._last_msg_sig:
            return

        # same room + same message count = an edit/tag change, so keep the scroll position
        prev = self._last_msg_sig
        keep_pos = (isinstance(prev, tuple) and prev[0] == self.selected_sub_room_id
                    and len(prev[1]) == len(rows))
        top = self._msg_canvas.yview()[0]
        self._last_msg_sig = sig

        # 3) rebuild
        for w in self.chat_messages_panel.winfo_children():
            w.destroy()
        self._img_refs.clear()

        if self.selected_is_private:
            banner = tk.Label(self.chat_messages_panel,
                               text="\U0001F512 Private conversation \u2014 only visible to "
                                    "participants and admins",
                               font=theme.font(10, slant="italic"), fg=theme.DM_COLOR,
                               bg="#f5ebff", anchor="w")
            banner.pack(fill="x", pady=(0, 6))

        last_date = ""
        for r in rows:
            sender = r["username"]
            fn = r["full_name"]
            sys_role = r["sys_role"]
            content = r["content"]
            priv = r["is_private"] == 1
            ts = r["sent_at"]
            date = ts.strftime("%Y-%m-%d")
            time_str = theme.fmt_time(ts)
            is_me = sender == self.current_username

            if date != last_date:
                self._build_date_separator(date).pack(fill="x", pady=(4, 4))
                last_date = date

            bubble = self._build_bubble(fn, sys_role, content, time_str, is_me, priv,
                                         r["msg_type"], r["message_id"], r["sender_id"],
                                         r["is_edited"], tag=r["msg_tag"],
                                         tag_label=r["msg_tag_label"])
            bubble.pack(fill="x", pady=(0, 5))

        self.after(50, lambda: self._scroll_chat(top if keep_pos else 1.0))

    def _scroll_chat(self, fraction):
        """Sizes the scroll area to the real message height, then scrolls.
        fraction 1.0 = bottom, where the latest message is."""
        try:
            self.update_idletasks()
            canvas = self._msg_canvas
            h = max(self.chat_messages_panel.winfo_reqheight(), canvas.winfo_height())
            canvas.configure(scrollregion=(0, 0, 584, h))
            canvas.yview_moveto(fraction)
        except tk.TclError:
            pass

    def _on_mousewheel(self, event):
        """Scrolls whichever list the pointer is over: chat, sub-rooms or members."""
        try:
            w = self.winfo_containing(event.x_root, event.y_root)
        except Exception:
            return
        targets = (self._msg_canvas, self._sr_canvas, self._members_canvas)
        while w is not None:
            for canvas in targets:
                if w is canvas:
                    num = getattr(event, "num", None)
                    if num == 4:
                        step = -1
                    elif num == 5:
                        step = 1
                    else:
                        step = -1 if event.delta > 0 else 1
                    canvas.yview_scroll(step * (2 if canvas is self._msg_canvas else 1),
                                        "units")
                    return
            w = w.master

    def show_no_permission(self, msg):
        for w in self.chat_messages_panel.winfo_children():
            w.destroy()
        tk.Label(self.chat_messages_panel, text=msg, font=theme.font(13, slant="italic"),
                 fg="#966464", bg=theme.CHAT_BG).pack(expand=True, pady=80)

    def _build_date_separator(self, date):
        wrap = tk.Frame(self.chat_messages_panel, bg=theme.CHAT_BG)
        tk.Frame(wrap, bg=theme.SOFT_BLUE, height=1).pack(side="left", fill="x", expand=True,
                                                            padx=(20, 8))
        tk.Label(wrap, text=date, font=theme.font(10), fg="#7896c8", bg=theme.CHAT_BG).pack(
            side="left")
        tk.Frame(wrap, bg=theme.SOFT_BLUE, height=1).pack(side="left", fill="x", expand=True,
                                                            padx=(8, 20))
        return wrap

    def _build_bubble(self, fn, sys_role, content, time_str, is_me, is_private, msg_type,
                      message_id, sender_id, is_edited, tag="none", tag_label=None):
        outer = tk.Frame(self.chat_messages_panel, bg=theme.CHAT_BG)

        if is_private:
            bubble_bg = "#ebdcff" if is_me else "#faf0ff"
        else:
            bubble_bg = theme.MSG_YOU_BG if is_me else theme.MSG_THEM_BG

        bubble_holder = tk.Frame(outer, bg=theme.CHAT_BG)
        bubble_holder.pack(side="right" if is_me else "left", padx=8)

        av_emoji = {"professor": "\U0001F468\u200D\U0001F3EB", "admin": "\U0001F6E1"}.get(sys_role, "\U0001F464")
        avatar = tk.Label(bubble_holder, text=av_emoji, font=theme.font(18, emoji=True),
                           bg=theme.CHAT_BG, width=2)

        bubble = tk.Frame(bubble_holder, bg=bubble_bg,
                           highlightbackground="#8c46d2" if is_private else bubble_bg,
                           highlightthickness=1 if is_private else 0)

        role_tag = {"professor": "  [Prof]", "admin": "  [Admin]"}.get(sys_role, "")
        priv_tag = "  \U0001F512" if is_private else ""
        sender_display = "You" if is_me else (fn or "User")
        sender_fg = (theme.DM_COLOR if is_me else "#7828c8") if is_private else \
            (theme.MEDIUM_BLUE if is_me else "#6441af")
        header = tk.Frame(bubble, bg=bubble_bg)
        header.pack(fill="x", padx=12, pady=(7, 0))
        tk.Label(header, text=f"{sender_display}{role_tag}{priv_tag}", font=theme.font(9, "bold"),
                 fg=sender_fg, bg=bubble_bg, anchor="w").pack(side="left")
        if tag and tag != "none":
            badge_text = (f"\U0001F3F7 {tag_label}" if tag == "other" and tag_label
                          else TAG_LABELS[tag])
            tk.Label(header, text=badge_text, font=theme.font(8, "bold", emoji=True),
                     fg="white", bg=TAG_COLORS[tag], padx=6).pack(side="left", padx=(8, 0))

        if msg_type == "image":
            img = imh.decode_base64_image(content)
            if img:
                photo = imh.make_photo(img, 260, 200)
                self._img_refs.append(photo)
                img_lbl = tk.Label(bubble, image=photo, bg=bubble_bg, cursor="hand2")
                img_lbl.pack(padx=12, pady=4)
                img_lbl.bind("<Button-1>", lambda e, im=img: imh.show_full_image(self, im))
            else:
                tk.Label(bubble, text="[Image could not be displayed]", bg=bubble_bg,
                         font=theme.font(11)).pack(padx=12, pady=4)
        elif msg_type == "emote":
            tk.Label(bubble, text=content, font=theme.font(38, emoji=True),
                     bg=bubble_bg).pack(padx=12, pady=4)
        elif msg_type in ("file", "video"):
            att = imh.decode_attachment(content)
            if att:
                _mime, fname, data = att
                kb = len(data) / 1024
                size_txt = f"{kb / 1024:.1f} MB" if kb >= 1024 else f"{kb:.0f} KB"
                icon = "\U0001F3AC" if msg_type == "video" else "\U0001F4C4"

                card = tk.Frame(bubble, bg=bubble_bg)
                card.pack(fill="x", padx=12, pady=4)
                tk.Label(card, text=icon, font=theme.font(24, emoji=True),
                         bg=bubble_bg).pack(side="left", padx=(0, 8))
                info = tk.Frame(card, bg=bubble_bg)
                info.pack(side="left")
                shown = fname if len(fname) <= 28 else fname[:25] + "..."
                tk.Label(info, text=shown, font=theme.font(11, "bold"),
                         fg=theme.DARK_NAVY, bg=bubble_bg, anchor="w").pack(anchor="w")
                tk.Label(info, text=size_txt, font=theme.font(9), fg="gray",
                         bg=bubble_bg, anchor="w").pack(anchor="w")

                btns = tk.Frame(bubble, bg=bubble_bg)
                btns.pack(fill="x", padx=12, pady=(0, 4))
                theme.make_button(btns, "Open", theme.MEDIUM_BLUE, font_size=9,
                                  command=lambda c=content: imh.open_attachment(c)
                                  ).pack(side="left", padx=(0, 6), ipadx=8)
                theme.make_button(btns, "Save", "#28376e", font_size=9,
                                  command=lambda c=content: imh.save_attachment(self, c)
                                  ).pack(side="left", ipadx=8)
            else:
                tk.Label(bubble, text="[File could not be displayed]", bg=bubble_bg,
                         font=theme.font(11)).pack(padx=12, pady=4)
        else:
            tk.Label(bubble, text=content, font=theme.font(12), fg=theme.DARK_NAVY, bg=bubble_bg,
                     anchor="w", justify="left", wraplength=320).pack(fill="x", padx=12, pady=4)

        footer = tk.Frame(bubble, bg=bubble_bg)
        footer.pack(fill="x", padx=12, pady=(0, 7))
        tk.Label(footer, text=time_str, font=theme.font(8), fg="gray",
                 bg=bubble_bg).pack(side="left")

        # Anyone can open the edit history
        if is_edited:
            lbl_edited = tk.Label(footer, text="  \u00b7 edited", font=theme.font(8, slant="italic"),
                                   fg=theme.MEDIUM_BLUE, bg=bubble_bg, cursor="hand2")
            lbl_edited.pack(side="left")
            lbl_edited.bind("<Button-1>", lambda e, mid=message_id: self.show_edit_history(mid))

        # Only the original sender (and only text messages) gets the Edit link
        if sender_id == self.current_user_id and msg_type == "text":
            lbl_edit = tk.Label(footer, text="  Edit", font=theme.font(8, "bold"),
                                 fg=theme.MEDIUM_BLUE, bg=bubble_bg, cursor="hand2")
            lbl_edit.pack(side="left")
            lbl_edit.bind("<Button-1>",
                          lambda e, mid=message_id, c=content: self.open_edit_dialog(mid, c))

        can_tag = sender_id == self.current_user_id and msg_type == "text"
        dots = None

        if is_me:
            if can_tag:
                # reserved space; the ⋯ only shows while hovering
                dots = tk.Label(bubble_holder, text="", width=2, font=theme.font(14, "bold"),
                                fg=theme.MEDIUM_BLUE, bg=theme.CHAT_BG, cursor="hand2")
                dots.pack(side="left")
            bubble.pack(side="left")
            avatar.pack(side="left")
        else:
            avatar.pack(side="left")
            bubble.pack(side="left")

        # Hover your own text message -> ⋯ appears -> click it to tag
        if can_tag and dots is not None:
            def open_tag_menu(_e=None):
                if not dots.cget("text"):
                    return
                menu = tk.Menu(self, tearoff=0)
                for key, label in TAG_LABELS.items():
                    if key == "none":
                        continue
                    menu.add_command(label=label,
                                     command=lambda k=key: self._on_menu_tag(message_id, k))
                if tag and tag != "none":
                    menu.add_separator()
                    menu.add_command(label="\u2716 Remove tag",
                                     command=lambda: self._on_menu_tag(message_id, "none"))
                try:
                    menu.tk_popup(dots.winfo_rootx(), dots.winfo_rooty() + dots.winfo_height())
                finally:
                    menu.grab_release()

            def show_dots(_e=None):
                try:
                    dots.configure(text="\u22EF")
                except tk.TclError:
                    pass

            def hide_dots(_e=None):
                try:
                    w = outer.winfo_containing(*outer.winfo_pointerxy())
                except Exception:
                    w = None
                while w is not None:      # still inside this message? keep the dots
                    if w is outer:
                        return
                    w = w.master
                try:
                    dots.configure(text="")
                except tk.TclError:
                    pass

            dots.bind("<Button-1>", open_tag_menu)
            self._bind_recursive(outer, "<Enter>", show_dots)
            self._bind_recursive(outer, "<Leave>", hide_dots)

        return outer

    def _bind_recursive(self, widget, sequence, callback):
        widget.bind(sequence, callback)
        for child in widget.winfo_children():
            self._bind_recursive(child, sequence, callback)

    def check_dm_preview(self):
        """Professors only: pops a small preview (student name + room name)
        when a new private message arrives in a DM they don't have open."""
        if self.current_sys_role != "professor":
            return
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT m.message_id, u.full_name, u.username, r.room_name
                FROM room_messages m
                JOIN users u ON u.user_id = m.sender_id
                JOIN room_sub_rooms sr ON sr.sub_room_id = m.sub_room_id
                JOIN rooms r ON r.room_id = sr.room_id
                WHERE m.is_private = 1 AND m.receiver_id = %s AND m.receiver_read = 0
                ORDER BY m.message_id DESC LIMIT 1
                """,
                (self.current_user_id,),
            )
            row = cur.fetchone()
            cur.close()
        except Exception:
            return
        if not row or row["message_id"] <= self._last_dm_toast_id:
            return
        self._last_dm_toast_id = row["message_id"]
        self._show_toast(row["full_name"] or row["username"], row["room_name"])

    def _show_toast(self, student, room_name):
        t = tk.Toplevel(self)
        t.overrideredirect(True)
        t.attributes("-topmost", True)
        t.configure(bg=theme.DM_BADGE_BG)
        tk.Label(t, text="New private message", font=theme.font(9, "bold"), fg="#e6d2ff",
                 bg=theme.DM_BADGE_BG, anchor="w").pack(fill="x", padx=12, pady=(8, 0))
        tk.Label(t, text=f"{student}  \u00b7  {room_name}", font=theme.font(11, "bold"),
                 fg="white", bg=theme.DM_BADGE_BG, anchor="w").pack(fill="x", padx=12, pady=(0, 8))
        x = self.winfo_rootx() + self.winfo_width() - 330
        y = self.winfo_rooty() + 40
        t.geometry(f"310x56+{x}+{y}")
        t.after(5000, t.destroy)

    def _on_menu_tag(self, message_id, key):
        if key == "other":
            self.prompt_other_label(message_id)
        else:
            self.set_message_tag(message_id, key)

    def prompt_other_label(self, message_id):
        """Asks for the required label when retagging a sent message as 'Other'."""
        if is_banned(self.current_user_id):
            return
        while True:
            label = simpledialog.askstring(
                "Other Tag", "Enter a label for this tag (required, max 20 characters):",
                parent=self)
            if label is None:          # cancelled
                return
            label = label.strip()
            if not label:
                messagebox.showwarning("Label Required",
                                       'You must enter a label for the "Other" tag.', parent=self)
                continue
            if len(label) > 20:
                messagebox.showwarning("Label Too Long",
                                       "The tag label can be at most 20 characters.", parent=self)
                continue
            break

        fr = filter_message(label, self.room_id)
        suspicious = find_suspicious(label)
        if fr.was_flagged or suspicious:
            log_flagged(self.current_user_id, message_id,
                        f"[tag label] {label}", f"[tag label] {fr.censored}",
                        category="suspicious" if suspicious else "filtered")
            if fr.was_flagged:
                show_warning_dialog(self, record_warning(self.current_user_id))
            else:
                messagebox.showinfo("Tag not saved",
                                     "That label wasn't saved. A host or administrator may follow up with you.",
                                     parent=self)
            return
        self.set_message_tag(message_id, "other", label)

    def set_message_tag(self, message_id, tag_key, label=None):
        """Changes the tag of one of the current user's own messages."""
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "UPDATE room_messages SET msg_tag=%s, msg_tag_label=%s "
                "WHERE message_id=%s AND sender_id=%s",
                (tag_key, label, message_id, self.current_user_id),
            )
            cur.close()
            self.refresh_messages()
        except Exception as ex:
            messagebox.showerror("Error", f"Error updating tag: {ex}", parent=self)

    # ═════════════════════════════════════════════════════════════════
    #  SEND MESSAGE — with profanity filter + warning/ban
    # ═════════════════════════════════════════════════════════════════
    def _on_tag_change(self, _e=None):
        """Shows the required label box when 'Other' is selected."""
        if TAG_KEYS.get(self.cmb_tag.get()) == "other":
            self.txt_message.place(x=102, y=14, width=208, height=36)
            self.txt_tag_label.place(x=316, y=14, width=94, height=36)
        else:
            self.txt_tag_label.place_forget()
            self.txt_message.place(x=102, y=14, width=308, height=36)

    def _clear_tag_label(self):
        e = self.txt_tag_label
        e.delete(0, tk.END)
        e.insert(0, e._placeholder)
        e.configure(fg="gray")
        e._is_placeholder = True
    
    def _reset_message_box(self):
        """Clears the input box after sending. If the box still has focus
        (e.g. right after pressing Enter), leaves it empty and ready to
        type; only restores the grey placeholder text if focus has left
        it, so the placeholder never gets typed into by mistake."""
        self.txt_message.delete(0, tk.END)
        self.cmb_tag.set(TAG_LABELS["none"])
        self._clear_tag_label()
        self._on_tag_change()
        if self.focus_get() is self.txt_message:
            self.txt_message.configure(fg=theme.DARK_NAVY)
        else:
            self.txt_message.insert(0, "Type a message...")
            self.txt_message.configure(fg="gray")

    def send_message(self):
        if self.selected_sub_room_id == -1:
            messagebox.showinfo("Info", "Please select a sub-room first.", parent=self)
            return

        raw_content = self.txt_message.get().strip()
        if not raw_content or raw_content == "Type a message...":
            return

        # Tag validation: "Other" requires a label
        tag_key = TAG_KEYS.get(self.cmb_tag.get(), "none")
        tag_label = None
        if tag_key == "other":
            tag_label = theme.entry_value(self.txt_tag_label)
            if not tag_label:
                messagebox.showwarning(
                    "Label Required",
                    'Please type a label for the "Other" tag before sending.', parent=self)
                self.txt_tag_label.focus_set()
                return
            if len(tag_label) > 20:
                messagebox.showwarning(
                    "Label Too Long",
                    "The tag label can be at most 20 characters.", parent=self)
                return

        if is_banned(self.current_user_id):
            messagebox.showerror(
                "Banned",
                "\u26d4 You are banned\n\nYou have been banned due to repeated profanity "
                "violations.\nContact an administrator to appeal.",
                parent=self,
            )
            return

        if not self._check_can_post():
            return

        fr = filter_message(raw_content, self.room_id)
        label_fr = filter_message(tag_label, self.room_id) if tag_label else None
        label_flagged = bool(label_fr and label_fr.was_flagged)
        filtered = fr.was_flagged or label_flagged
        suspicious = find_suspicious(raw_content)

        # Banned / filtered / suspicious: never reaches the chat. The admins of this
        # department and the host get an alert and can talk to the sender privately.
        if filtered or suspicious:
            log_flagged(
                self.current_user_id, None,
                raw_content if (fr.was_flagged or suspicious) else f"[tag label] {tag_label}",
                fr.censored,
                category="suspicious" if suspicious else "filtered",
                sub_room_id=self.selected_sub_room_id,
            )
            if filtered:
                warn_count = record_warning(self.current_user_id)
                show_warning_dialog(self, warn_count)
                if is_banned(self.current_user_id):
                    self.txt_message.delete(0, tk.END)
                    self.txt_message.configure(fg="gray", state="disabled")
                    self.btn_send.configure(state="disabled")
                    return
            else:
                messagebox.showinfo(
                    "Message not sent",
                    "Your message was not sent. A host or administrator may follow up with you.",
                    parent=self)
            self._reset_message_box()
            return

        try:
            conn = get_connection()
            cur = conn.cursor()
            receiver_id = self.selected_dm_partner_id if (self.selected_is_private and
                                                            self.selected_dm_partner_id != -1) else None
            cur.execute(
                "INSERT INTO room_messages (sub_room_id, sender_id, content, is_private, "
                "receiver_id, msg_tag, msg_tag_label) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (self.selected_sub_room_id, self.current_user_id, raw_content,
                 1 if self.selected_is_private else 0, receiver_id, tag_key, tag_label),
            )
            cur.close()

            self._reset_message_box()
            self.refresh_messages()

        except Exception as ex:
            messagebox.showerror("Error", f"Error sending: {ex}", parent=self)

    # ═════════════════════════════════════════════════════════════════
    #  EDIT MESSAGE + EDIT HISTORY
    # ═════════════════════════════════════════════════════════════════
    def open_edit_dialog(self, message_id, current_content):
        dlg = tk.Toplevel(self)
        dlg.title("Edit Message")
        dlg.geometry("440x210")
        dlg.transient(self)
        dlg.grab_set()
        dlg.configure(bg=theme.SUB_ROOM_BG)
        dlg.resizable(False, False)

        tk.Label(dlg, text="Edit your message", font=theme.font(13, "bold"), fg="white",
                 bg=theme.SUB_ROOM_BG, anchor="w").place(x=20, y=14, width=400, height=22)
        tk.Label(dlg, text="The edit history will be visible to everyone in this conversation.",
                 font=theme.font(10, slant="italic"), fg=theme.SOFT_BLUE, bg=theme.SUB_ROOM_BG,
                 anchor="w").place(x=20, y=38, width=400, height=16)

        entry = tk.Entry(dlg, font=theme.font(12), bg="white", fg=theme.DARK_NAVY,
                         relief="solid", bd=1, highlightthickness=1,
                         highlightbackground=theme.SOFT_BLUE)
        entry.insert(0, current_content)
        entry.place(x=20, y=64, width=400, height=36)
        entry.focus_set()

        status = tk.Label(dlg, text="", font=theme.font(10), fg="#ff8080",
                          bg=theme.SUB_ROOM_BG, anchor="center")
        status.place(x=20, y=106, width=400, height=18)

        def save():
            new_text = entry.get().strip()
            if not new_text:
                status.configure(text="Message can't be empty.")
                return
            if is_banned(self.current_user_id):
                status.configure(text="You are banned and can't edit messages.")
                return

            try:
                conn = get_connection()
                cur = conn.cursor()

                # Re-read from the DB: confirms ownership and gets the true "before" text
                cur.execute(
                    "SELECT content FROM room_messages "
                    "WHERE message_id=%s AND sender_id=%s AND msg_type='text'",
                    (message_id, self.current_user_id),
                )
                row = cur.fetchone()
                if not row:
                    cur.close()
                    status.configure(text="You can only edit your own messages.")
                    return
                old_content = row[0]

                if new_text == old_content:
                    cur.close()
                    dlg.destroy()
                    return

                fr = filter_message(new_text, self.room_id)
                suspicious = find_suspicious(new_text)
                if fr.was_flagged or suspicious:
                    cur.close()
                    log_flagged(self.current_user_id, message_id, new_text, fr.censored,
                                category="suspicious" if suspicious else "filtered")
                    if fr.was_flagged:
                        show_warning_dialog(dlg, record_warning(self.current_user_id))
                    else:
                        messagebox.showinfo(
                            "Edit not saved",
                            "Your edit was not saved. A host or administrator may follow up with you.",
                            parent=dlg)
                    dlg.destroy()
                    return
                final_content = new_text

                cur.execute(
                    "UPDATE room_messages SET content=%s, is_edited=1, edited_at=NOW() "
                    "WHERE message_id=%s AND sender_id=%s",
                    (final_content, message_id, self.current_user_id),
                )
                cur.execute(
                    "INSERT INTO message_edits (message_id, old_content, new_content) "
                    "VALUES (%s,%s,%s)",
                    (message_id, old_content, final_content),
                )
                cur.close()

                dlg.destroy()
                self.refresh_messages()
            except Exception as ex:
                status.configure(text=f"Error: {ex}")

        btn_save = theme.make_button(dlg, "Save Edit", theme.MEDIUM_BLUE, font_size=12,
                                      command=save)
        btn_save.place(x=100, y=136, width=110, height=36)
        btn_cancel = theme.make_button(dlg, "Cancel", "#28376e", font_size=12,
                                        command=dlg.destroy)
        btn_cancel.place(x=230, y=136, width=110, height=36)
        entry.bind("<Return>", lambda e: save())

    def show_edit_history(self, message_id):
        dlg = tk.Toplevel(self)
        dlg.title("Edit History")
        dlg.geometry("480x380")
        dlg.transient(self)
        dlg.configure(bg=theme.SUB_ROOM_BG)

        tk.Label(dlg, text="Edit History", font=theme.font(13, "bold"), fg="white",
                 bg=theme.SUB_ROOM_BG, anchor="w").place(x=16, y=12, width=440, height=22)

        txt = tk.Text(dlg, wrap="word", font=theme.font(11), bg="#1c2a55", fg="white",
                      relief="flat", padx=8, pady=8)
        txt.place(x=16, y=44, width=448, height=320)

        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT old_content, new_content, edited_at FROM message_edits "
                "WHERE message_id=%s ORDER BY edited_at ASC, edit_id ASC",
                (message_id,),
            )
            rows = cur.fetchall()
            cur.close()
            if not rows:
                txt.insert(tk.END, "No edits recorded.")
            for r in rows:
                txt.insert(tk.END, f'{theme.fmt_datetime(r["edited_at"])}\n'
                                   f'  Before: {r["old_content"]}\n'
                                   f'  After:  {r["new_content"]}\n\n')
        except Exception as ex:
            txt.insert(tk.END, f"Error loading history: {ex}")
        txt.configure(state="disabled")

    def _check_can_post(self, upload=False):
        """Warns and returns False if the user can't send (or upload) in the selected sub-room."""
        if self.selected_is_private or self.current_sys_role == "admin":
            return True
        _r, can_send, can_upload = self.channel_perms(self.selected_sub_room_id)
        if upload:
            if can_upload:
                return True
            msg = "You don't have permission to upload files in this sub-room."
        else:
            if can_send:
                return True
            msg = "You don't have permission to send messages in this sub-room."
        messagebox.showwarning("Permission Denied", msg, parent=self)
        return False

    def _is_host_or_admin(self):
        if self.current_sys_role == "admin":
            return True
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT room_role FROM room_members WHERE room_id=%s AND user_id=%s",
                        (self.room_id, self.current_user_id))
            row = cur.fetchone()
            cur.close()
            return bool(row and row[0] == "host")
        except Exception:
            return False

    def channel_perms(self, sub_room_id):
        """(can_read, can_send, can_upload) for the current user in a public sub-room.
        Admins and the host always have everything. Everyone else gets 'Everyone' plus all
        their roles combined, limited by their personal Can Read History / Can Send
        Messages switches in Room Settings."""
        if self.current_sys_role == "admin":
            return True, True, True
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT room_role, can_send_messages, can_read_history FROM room_members "
                "WHERE room_id=%s AND user_id=%s", (self.room_id, self.current_user_id))
            me = cur.fetchone()
            if not me:
                cur.close()
                return False, False, False
            if me["room_role"] == "host":
                cur.close()
                return True, True, True
            cur.execute(
                "SELECT everyone_read, everyone_send, everyone_upload FROM room_sub_rooms "
                "WHERE sub_room_id=%s", (sub_room_id,))
            ev = cur.fetchone()
            cur.execute(
                "SELECT COALESCE(MAX(p.can_read),0) AS r, COALESCE(MAX(p.can_send),0) AS s, "
                "COALESCE(MAX(p.can_upload),0) AS u "
                "FROM sub_room_role_perms p JOIN room_member_roles mr ON mr.role_id = p.role_id "
                "WHERE p.sub_room_id=%s AND mr.user_id=%s", (sub_room_id, self.current_user_id))
            rl = cur.fetchone()
            cur.close()
        except Exception as ex:
            print(f"channel_perms error: {ex}")
            return False, False, False
        if not ev:
            return False, False, False
        can_read = (ev["everyone_read"] == 1 or rl["r"] == 1) and me["can_read_history"] == 1
        can_send = (ev["everyone_send"] == 1 or rl["s"] == 1) and me["can_send_messages"] == 1
        can_upload = (ev["everyone_upload"] == 1 or rl["u"] == 1) and me["can_send_messages"] == 1
        return bool(can_read), bool(can_send), bool(can_upload)

    def _readable_sub_room_ids(self):
        """None = everything (admin / host). Otherwise the public sub-room ids this user can read."""
        if self._is_host_or_admin():
            return None
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT s.sub_room_id FROM room_sub_rooms s "
                "WHERE s.room_id=%s AND s.sub_room_type_detail='public' AND (s.everyone_read=1 "
                "OR EXISTS (SELECT 1 FROM sub_room_role_perms p "
                "JOIN room_member_roles mr ON mr.role_id = p.role_id "
                "WHERE p.sub_room_id = s.sub_room_id AND p.can_read = 1 AND mr.user_id = %s))",
                (self.room_id, self.current_user_id))
            ids = {r[0] for r in cur.fetchall()}
            cur.close()
            return ids
        except Exception:
            return None
        
    # ═════════════════════════════════════════════════════════════════
    #  PERMISSIONS
    # ═════════════════════════════════════════════════════════════════
    def get_permission(self, column):
        # only admins bypass; the host's stored permissions are respected
        if self.current_sys_role == "admin":
            return True
        if column not in ("can_send_messages", "can_read_history", "can_manage_members"):
            return False
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                f"SELECT {column} FROM room_members WHERE room_id=%s AND user_id=%s",
                (self.room_id, self.current_user_id),
            )
            row = cur.fetchone()
            cur.close()
            if row:
                return row[0] == 1
        except Exception:
            pass
        return True

    def apply_permissions_to_input(self):
        if (self.selected_is_private or self.current_sys_role == "admin"
                or self.selected_sub_room_id == -1):
            allowed = True
        else:
            allowed = self.channel_perms(self.selected_sub_room_id)[1]

        self.btn_send.configure(state="normal" if allowed else "disabled")
        self.txt_message.configure(state="normal")
        if allowed:
            if self.txt_message.get() == RESTRICTED_MSG:
                self.txt_message.delete(0, tk.END)
                self.txt_message.insert(0, "Type a message...")
                self.txt_message.configure(fg="gray")
        else:
            if self.txt_message.get() != RESTRICTED_MSG:
                self.txt_message.delete(0, tk.END)
                self.txt_message.insert(0, RESTRICTED_MSG)
            self.txt_message.configure(fg="#a05050", state="disabled")

    # ═════════════════════════════════════════════════════════════════
    #  ROOM SETTINGS (host / admin only)
    # ═════════════════════════════════════════════════════════════════
    def open_room_settings(self):
        dlg = tk.Toplevel(self)
        dlg.title(f"\u2699  Room Settings \u2014 {self.room_name}")
        dlg.geometry("560x665")
        dlg.transient(self)
        dlg.grab_set()
        dlg.configure(bg="#233260")
        dlg.resizable(False, False)

        tk.Label(dlg, text="\u2699  Room Settings", font=theme.font(16, "bold"), fg="white",
                 bg="#233260", anchor="w").place(x=20, y=18, width=400, height=26)
        tk.Label(dlg, text=f"Room: {self.room_name}   |   Room ID: {self.room_id}",
                 font=theme.font(11), fg=theme.SOFT_BLUE, bg="#233260",
                 anchor="w").place(x=20, y=44, width=520, height=18)
        self._dlg_sep(dlg, 68)

        tk.Label(dlg, text=f"Invite Code:  {self._get_invite_code()}", font=theme.font(12, "bold"),
                 fg="#78dc82", bg="#233260", anchor="w").place(x=20, y=78, width=520, height=20)
        self._dlg_sep(dlg, 108)

        tk.Label(dlg, text="Member Permissions", font=theme.font(13, "bold"), fg="white",
                 bg="#233260", anchor="w").place(x=20, y=118, width=520, height=20)

        theme.make_button(dlg, "\U0001F3AD  Manage Roles", theme.DM_BADGE_BG, font_size=10,
                          emoji=True, command=lambda: self.open_roles_dialog(dlg)
                          ).place(x=380, y=114, width=160, height=26)

        perm_data = {}   # listbox text -> DB row
        lb_members = tk.Listbox(dlg, bg="#1c2a55", fg="white", font=theme.font(11),
                                 selectbackground=theme.MEDIUM_BLUE, exportselection=False,
                                 highlightthickness=1, highlightbackground=theme.MEDIUM_BLUE)
        lb_members.place(x=20, y=148, width=250, height=104)

        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT u.user_id, u.full_name, u.username, rm.room_role,
                       rm.can_send_messages, rm.can_read_history, rm.can_manage_members,
                       rm.can_post_announcements
                FROM room_members rm
                JOIN users u ON u.user_id = rm.user_id
                WHERE rm.room_id = %s AND (rm.room_role != 'host' OR %s) AND u.role != 'admin'
                ORDER BY FIELD(rm.room_role,'host','member'), u.full_name ASC
                """,
                (self.room_id, self.current_sys_role == "admin"),
            )
            for r in cur.fetchall():
                label = f'{r["full_name"] or r["username"]} (@{r["username"]})'
                if r["room_role"] == "host":
                    label += "  [HOST]"
                perm_data[label] = r
                lb_members.insert(tk.END, label)
            cur.close()
        except Exception as ex:
            print(f"Settings member list error: {ex}")

        lbl_sel = tk.Label(dlg, text="Select a member", font=theme.font(11, "bold"),
                            fg="#a0c8ff", bg="#233260", anchor="w")
        lbl_sel.place(x=285, y=148, width=255, height=18)
        cb_send = self._perm_check(dlg, "Can Send Messages", True)
        cb_send.place(x=285, y=168, width=240, height=22)
        cb_read = self._perm_check(dlg, "Can Read History", True)
        cb_read.place(x=285, y=190, width=240, height=22)
        cb_manage = self._perm_check(dlg, "Can Manage Members", False)
        cb_manage.place(x=285, y=212, width=240, height=22)



        def on_pick(_e=None):
            sel = lb_members.curselection()
            if not sel:
                return
            label = lb_members.get(sel[0])
            r = perm_data[label]
            lbl_sel.configure(text=label[:32])
            cb_send.var.set(r["can_send_messages"] == 1)
            cb_read.var.set(r["can_read_history"] == 1)
            cb_manage.var.set(r["can_manage_members"] == 1)
            

        lb_members.bind("<<ListboxSelect>>", on_pick)

        self._dlg_sep(dlg, 262)

        tk.Label(dlg, text="Sub-Rooms", font=theme.font(13, "bold"), fg="white", bg="#233260",
                 anchor="w").place(x=20, y=275, width=520, height=20)

        sr_canvas = tk.Canvas(dlg, bg="#1c2a55", highlightthickness=1,
                               highlightbackground=theme.MEDIUM_BLUE, yscrollincrement=32)
        sr_canvas.place(x=20, y=298, width=504, height=120)
        sr_scroll = tk.Scrollbar(dlg, orient="vertical", command=sr_canvas.yview)
        sr_canvas.configure(yscrollcommand=sr_scroll.set)
        sr_scroll.place(x=524, y=298, width=16, height=120)
        sub_room_list_panel = tk.Frame(sr_canvas, bg="#1c2a55")
        sr_canvas.create_window((0, 0), window=sub_room_list_panel, anchor="nw", width=502)
        sub_room_list_panel.bind(
            "<Configure>",
            lambda e: sr_canvas.configure(
                scrollregion=(0, 0, 502, max(e.height, sr_canvas.winfo_height()))))

        # mouse wheel for this dialog's sub-room list (one notch = one row)
        def on_wheel(event):
            try:
                w = dlg.winfo_containing(event.x_root, event.y_root)
            except Exception:
                return
            while w is not None:
                if w is sr_canvas:
                    num = getattr(event, "num", None)
                    if num == 4:
                        step = -1
                    elif num == 5:
                        step = 1
                    else:
                        step = -1 if event.delta > 0 else 1
                    sr_canvas.yview_scroll(step, "units")
                    return
                w = w.master

        dlg.bind("<MouseWheel>", on_wheel)
        dlg.bind("<Button-4>", on_wheel)
        dlg.bind("<Button-5>", on_wheel)

        def refresh_list():
            for w in sub_room_list_panel.winfo_children():
                w.destroy()
            try:
                conn = get_connection()
                cur = conn.cursor(dictionary=True)
                cur.execute(
                    "SELECT s.sub_room_id, s.sub_room_name, s.sub_room_type, "
                    "s.sub_room_type_detail, "
                    "COALESCE(NULLIF(ua.full_name,''), ua.username) AS dm_a_name, "
                    "COALESCE(NULLIF(ub.full_name,''), ub.username) AS dm_b_name "
                    "FROM room_sub_rooms s "
                    "LEFT JOIN users ua ON ua.user_id = s.dm_user_a "
                    "LEFT JOIN users ub ON ub.user_id = s.dm_user_b "
                    "WHERE s.room_id=%s AND (s.sub_room_type_detail='public' OR %s) "
                    "ORDER BY s.position ASC",
                    (self.room_id, self.current_sys_role == "admin"),
                )
                rows = cur.fetchall()
                cur.close()

                for r in rows:
                    sr_id, sr_name = r["sub_room_id"], r["sub_room_name"]
                    sr_type, detail = r["sub_room_type"], r["sub_room_type_detail"]
                    is_dm = detail == "private"
                    if is_dm:
                        sr_name = f"DM-{r['dm_a_name']} \u2194 {r['dm_b_name']}"

                    row_f = tk.Frame(sub_room_list_panel, bg="#1c2a55", height=32)
                    row_f.pack(fill="x")
                    row_f.pack_propagate(False)

                    icon = "\U0001F512" if is_dm else ("\U0001F4E2" if sr_type == "announcement" else "\u25B8")
                    tk.Label(row_f, text=icon, font=theme.font(12, emoji=True),
                             fg="#be82ff" if is_dm else theme.SOFT_BLUE,
                             bg="#1c2a55").place(x=8, y=6, width=20, height=20)
                    tk.Label(row_f, text=sr_name,
                             font=theme.font(12), fg="#c8a0ff" if is_dm else "white",
                             bg="#1c2a55", anchor="w").place(x=32, y=7, width=420, height=18)

                    if not is_dm:
                        def make_delete(srid=sr_id, name=sr_name):
                            def _del():
                                if messagebox.askyesno(
                                        "Delete Sub-Room",
                                        f'Delete "{name}"? All messages will be lost.',
                                        parent=dlg):
                                    self.delete_sub_room(srid)
                                    if srid == self.selected_sub_room_id:
                                        self.selected_sub_room_id = -1
                                        self.lbl_sub_room_header.configure(text="\u25B8 Select a sub-room")
                                        for cw in self.chat_messages_panel.winfo_children():
                                            cw.destroy()
                                    self.load_sub_rooms()
                                    refresh_list()
                            return _del

                        btn_del = tk.Button(row_f, text="\U0001F5D1", font=theme.font(11, emoji=True),
                                             fg="white", bg=theme.RED_ACCENT, relief="flat", bd=0,
                                             cursor="hand2", command=make_delete())
                        btn_del.place(x=456, y=5, width=38, height=22)
                        btn_perm = tk.Button(
                            row_f, text="\U0001F511", font=theme.font(11, emoji=True),
                            fg="white", bg=theme.MEDIUM_BLUE, relief="flat", bd=0,
                            cursor="hand2",
                            command=lambda i=sr_id, n=sr_name:
                                self.open_channel_perms_dialog(i, n, dlg))
                        btn_perm.place(x=412, y=5, width=38, height=22)

            except Exception as ex:
                print(f"Settings sub-room list error: {ex}")

        refresh_list()

        tf_new = tk.Entry(dlg, font=theme.font(12), bg="white", fg=theme.DARK_NAVY,
                           relief="solid", bd=1, highlightthickness=1,
                           highlightbackground=theme.SOFT_BLUE)
        tf_new.place(x=20, y=428, width=260, height=30)

        def do_add():
            import re
            sr_name = re.sub(r"[^a-z0-9\-]", "-", tf_new.get().strip().lower())
            if not sr_name:
                return
            new_id = self.add_sub_room(sr_name)
            tf_new.delete(0, tk.END)
            self.load_sub_rooms()
            refresh_list()
            if new_id:
                self.open_channel_perms_dialog(new_id, sr_name, dlg)

        btn_add = theme.make_button(dlg, "+ Add Sub-Room", theme.MEDIUM_BLUE, font_size=11,
                                     command=do_add)
        btn_add.place(x=290, y=428, width=160, height=30)

        self._dlg_sep(dlg, 470)

        if self.current_sys_role == "admin":
            btn_flagged = theme.make_button(dlg, "\U0001F4CB View Flagged Messages",
                                             theme.WARN_ORANGE, font_size=10, emoji=True,
                                             command=lambda: self.open_flagged_messages_viewer(dlg))
            btn_flagged.place(x=20, y=480, width=220, height=28)

        if self.my_room_role == "host" or self.current_sys_role == "admin":
            def do_delete_room():
                if messagebox.askyesno(
                        "Delete Room",
                        f'Permanently delete room "{self.room_name}"?\nThis cannot be undone!',
                        parent=dlg, icon="warning"):
                    dlg.destroy()
                    self.delete_room()

            btn_del_room = theme.make_button(dlg, "\U0001F5D1  Delete Entire Room",
                                              theme.RED_ACCENT, font_size=11, emoji=True,
                                              command=do_delete_room)
            btn_del_room.place(x=290, y=480, width=240, height=28)

        self._dlg_sep(dlg, 520)

        save_status = tk.Label(dlg, text="", font=theme.font(11, "bold"), bg="#233260",
                                anchor="center")
        save_status.place(x=20, y=530, width=520, height=18)

        def do_save():
            sel = lb_members.curselection()
            if not sel:
                save_status.configure(fg="#ff8080", text="Select a member first.")
                return
            label = lb_members.get(sel[0])
            r = perm_data[label]
            s, rd, m = bool(cb_send.var.get()), bool(cb_read.var.get()), bool(cb_manage.var.get())
            self.save_member_perms(r["user_id"], s, rd, m)
            r["can_send_messages"], r["can_read_history"], r["can_manage_members"] = int(s), int(rd), int(m)
            
            save_status.configure(fg="#50d250", text=f"\u2713 Saved for {label[:30]}")

        btn_save = theme.make_button(dlg, "Save Permissions", theme.MEDIUM_BLUE, font_size=13,
                                      command=do_save)
        btn_save.place(x=165, y=552, width=230, height=38)
        if self.my_room_role == "host" or self.current_sys_role == "admin":
            is_arch = self._room_is_archived()

            def do_toggle_archive():
                if not is_arch:
                     if not messagebox.askyesno(
                            "Archive Room",
                            f'Archive "{self.room_name}"?\n\nMembers will no longer see it in '
                            "their dashboard. You and administrators can still open it and "
                            "restore it later from the \U0001F4E6 Archived button at the "
                            "bottom left of the lobby.", parent=dlg):
                        return
                if not self.set_room_archived(not is_arch):
                    messagebox.showwarning("Not allowed",
                                            "Only the host or an administrator can do that.",
                                            parent=dlg)
                    return
                dlg.destroy()
                self.go_back()

            btn_archive = theme.make_button(
                dlg, "\u267B  Restore Room" if is_arch else "\U0001F4E6  Archive Room",
                theme.WARN_ORANGE, font_size=11, emoji=True, command=do_toggle_archive)
            btn_archive.place(x=165, y=600, width=230, height=34)

    def _perm_check(self, dlg, label, selected):
        var = tk.BooleanVar(value=selected)
        cb = tk.Checkbutton(dlg, text=label, variable=var, font=theme.font(11), fg="white",
                             bg="#233260", selectcolor="#233260", activebackground="#233260",
                             activeforeground="white")
        cb.var = var
        return cb

    def open_flagged_messages_viewer(self, parent_dlg):
        dlg = tk.Toplevel(parent_dlg)
        dlg.title("\U0001F4CB Flagged Messages (Admin View)")
        dlg.geometry("700x500")
        dlg.transient(parent_dlg)
        dlg.grab_set()
        dlg.configure(bg="#19233c")

        tk.Label(dlg, text="Flagged & Suspicious Messages  \u2014  your departments only",
                 font=theme.font(13, "bold"), fg=theme.WARN_ORANGE, bg="#19233c",
                 anchor="w").place(x=14, y=12, width=670, height=22)

        cols = ("Room", "Sub-room", "Sender", "Type", "Original Message", "Status", "Time")
        tree = ttk.Treeview(dlg, columns=cols, show="headings", height=17)
        for c, w in zip(cols, (70, 130, 70, 70, 100, 130, 98)):
            tree.heading(c, text=c)
            tree.column(c, width=w)
        tree.tag_configure("unread", foreground=theme.RED_ACCENT)
        tree.place(x=14, y=44, width=668, height=410)

        try:
            rows = get_admin_flagged(self.current_user_id, is_admin=self.current_sys_role == "admin")
            for r in rows:
                suspicious = r["category"] == "suspicious"
                tree.insert("", tk.END, tags=("unread",) if r["is_unread"] else (), values=(
                    r["room_name"],
                    (f"DM-{r['dm_a_name']} \u2194 {r['dm_b_name']}"
                     if r["sub_room_type_detail"] == "private" else r["sub_room_name"]),
                    r["username"],
                    "Suspicious" if suspicious else "Filtered",
                    r["original"],
                    "Held back",
                    theme.fmt_datetime(r["flagged_at"]),
                ))
            # only now does it count as read, and only for this admin
            mark_alerts_read(self.current_user_id,
                             [r["id"] for r in rows if r["is_unread"]])
            self.check_admin_alerts()
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=dlg)

    # ═════════════════════════════════════════════════════════════════
    #  FILTERED WORDS (professor / admin)
    # ═════════════════════════════════════════════════════════════════
    def open_roles_dialog(self, parent_dlg):
        if not self._is_host_or_admin():
            return
        bg = theme.SUB_ROOM_BG
        dlg = tk.Toplevel(parent_dlg)
        dlg.title("Manage Roles")
        dlg.geometry("560x450")
        dlg.transient(parent_dlg)
        dlg.grab_set()
        dlg.configure(bg=bg)
        dlg.resizable(False, False)

        def close():
            dlg.destroy()
            try:
                parent_dlg.grab_set()
            except tk.TclError:
                pass
        dlg.protocol("WM_DELETE_WINDOW", close)

        tk.Label(dlg, text="Custom Roles", font=theme.font(14, "bold"), fg="white",
                 bg=bg, anchor="w").place(x=20, y=14, width=520, height=24)
        tk.Label(dlg, text="Create a role and give it to members. Then use the key button "
                           "next to a sub-room in Room Settings to choose what each role can "
                           "read, send and upload there.",
                 font=theme.font(10, slant="italic"), fg=theme.SOFT_BLUE, bg=bg, anchor="w",
                 wraplength=520, justify="left").place(x=20, y=40, width=520, height=32)
        tk.Label(dlg, text="ROLES", font=theme.font(10, "bold"), fg="#8ca5d2", bg=bg,
                 anchor="w").place(x=20, y=80, width=240, height=16)
        tk.Label(dlg, text="MEMBERS  (double-click to give / remove)", font=theme.font(10, "bold"),
                 fg="#8ca5d2", bg=bg, anchor="w").place(x=280, y=80, width=260, height=16)

        lb_kw = dict(bg="#1c2a55", fg="white", font=theme.font(12),
                     selectbackground=theme.MEDIUM_BLUE, exportselection=False,
                     highlightthickness=1, highlightbackground=theme.MEDIUM_BLUE)
        lb_roles = tk.Listbox(dlg, **lb_kw)
        lb_roles.place(x=20, y=100, width=240, height=230)
        lb_people = tk.Listbox(dlg, **lb_kw)
        lb_people.place(x=280, y=100, width=260, height=230)

        status = tk.Label(dlg, text="", font=theme.font(10), bg=bg, anchor="center")
        status.place(x=20, y=338, width=520, height=18)
        tf_name = tk.Entry(dlg, font=theme.font(12), bg="white", fg=theme.DARK_NAVY,
                           relief="solid", bd=1, highlightthickness=1,
                           highlightbackground=theme.SOFT_BLUE)
        tf_name.place(x=20, y=364, width=240, height=30)

        roles = []     # (role_id, name)
        people = []    # (user_id, has_role)

        def say(msg, ok=False):
            status.configure(fg="#50d250" if ok else "#ff8080", text=msg)

        def selected_role():
            sel = lb_roles.curselection()
            return roles[sel[0]] if sel else None

        def load_people():
            lb_people.delete(0, tk.END)
            people.clear()
            role = selected_role()
            try:
                conn = get_connection()
                cur = conn.cursor(dictionary=True)
                cur.execute(
                    "SELECT u.user_id, u.full_name, u.username, "
                    "EXISTS(SELECT 1 FROM room_member_roles mr "
                    "       WHERE mr.role_id=%s AND mr.user_id=u.user_id) AS has_role "
                    "FROM room_members rm JOIN users u ON u.user_id = rm.user_id "
                    "WHERE rm.room_id=%s AND rm.room_role != 'host' AND u.role != 'admin' "
                    "ORDER BY u.full_name ASC",
                    (role[0] if role else 0, self.room_id))
                for r in cur.fetchall():
                    has = r["has_role"] == 1
                    lb_people.insert(tk.END, ("\u2713  " if has else "     ") +
                                     f'{r["full_name"] or r["username"]} (@{r["username"]})')
                    people.append((r["user_id"], has))
                cur.close()
            except Exception as ex:
                say(f"Error: {ex}")

        def load_roles(select_id=None):
            lb_roles.delete(0, tk.END)
            roles.clear()
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("SELECT role_id, role_name FROM room_roles WHERE room_id=%s "
                            "ORDER BY role_name ASC", (self.room_id,))
                for rid, name in cur.fetchall():
                    roles.append((rid, name))
                    lb_roles.insert(tk.END, name)
                    if rid == select_id:
                        lb_roles.selection_set(tk.END)
                cur.close()
            except Exception as ex:
                say(f"Error: {ex}")
            load_people()

        def toggle_person(e):
            role = selected_role()
            if not role:
                say("Select a role first.")
                return
            idx = lb_people.nearest(e.y)
            if not (0 <= idx < len(people)):
                return
            uid, has = people[idx]
            try:
                conn = get_connection()
                cur = conn.cursor()
                if has:
                    cur.execute("DELETE FROM room_member_roles WHERE role_id=%s AND user_id=%s",
                                (role[0], uid))
                else:
                    cur.execute("INSERT IGNORE INTO room_member_roles (room_id, user_id, role_id) "
                                "VALUES (%s,%s,%s)", (self.room_id, uid, role[0]))
                cur.close()
            except Exception as ex:
                say(f"Error: {ex}")
                return
            load_people()
            lb_people.selection_set(idx)
            say("")

        def do_create():
            name = tf_name.get().strip()
            if not name:
                say("Type a role name first.")
                return
            if len(name) > 30:
                say("Role name can be at most 30 characters.")
                return
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("INSERT INTO room_roles (room_id, role_name) VALUES (%s,%s)",
                            (self.room_id, name))
                new_id = cur.lastrowid
                cur.close()
            except Exception as ex:
                say("A role with that name already exists." if getattr(ex, "errno", None) == 1062
                    else f"Error: {ex}")
                return
            tf_name.delete(0, tk.END)
            load_roles(new_id)
            say("\u2713 Role created.", ok=True)

        def do_rename():
            role = selected_role()
            name = tf_name.get().strip()
            if not role or not name:
                say("Select a role and type its new name.")
                return
            if len(name) > 30:
                say("Role name can be at most 30 characters.")
                return
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("UPDATE room_roles SET role_name=%s WHERE role_id=%s AND room_id=%s",
                            (name, role[0], self.room_id))
                cur.close()
            except Exception as ex:
                say("A role with that name already exists." if getattr(ex, "errno", None) == 1062
                    else f"Error: {ex}")
                return
            tf_name.delete(0, tk.END)
            load_roles(role[0])
            say("\u2713 Role renamed.", ok=True)

        def do_delete():
            role = selected_role()
            if not role:
                say("Select a role first.")
                return
            if not messagebox.askyesno(
                    "Delete Role",
                    f'Delete "{role[1]}"? Members lose it and its sub-room permissions.',
                    parent=dlg):
                return
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM room_roles WHERE role_id=%s AND room_id=%s",
                            (role[0], self.room_id))
                cur.close()
            except Exception as ex:
                say(f"Error: {ex}")
                return
            load_roles()
            say("\u2713 Role deleted.", ok=True)

        lb_roles.bind("<<ListboxSelect>>", lambda e: load_people())
        lb_people.bind("<Double-Button-1>", toggle_person)
        tf_name.bind("<Return>", lambda e: do_create())

        theme.make_button(dlg, "Create", theme.MEDIUM_BLUE, font_size=11,
                          command=do_create).place(x=20, y=402, width=76, height=30)
        theme.make_button(dlg, "Rename", "#28376e", font_size=11,
                          command=do_rename).place(x=102, y=402, width=76, height=30)
        theme.make_button(dlg, "Delete", theme.RED_ACCENT, font_size=11,
                          command=do_delete).place(x=184, y=402, width=76, height=30)
        theme.make_button(dlg, "Close", "#28376e", font_size=11,
                          command=close).place(x=420, y=402, width=120, height=30)

        load_roles()

    def open_channel_perms_dialog(self, sr_id, sr_name, parent_dlg):
        if not self._is_host_or_admin():
            return
        bg = theme.SUB_ROOM_BG
        dlg = tk.Toplevel(parent_dlg)
        dlg.title(f"Permissions \u2014 {sr_name}")
        dlg.geometry("520x440")
        dlg.transient(parent_dlg)
        dlg.grab_set()
        dlg.configure(bg=bg)
        dlg.resizable(False, False)

        def close():
            dlg.destroy()
            try:
                parent_dlg.grab_set()
            except tk.TclError:
                pass
        dlg.protocol("WM_DELETE_WINDOW", close)

        tk.Label(dlg, text=f"Who can use  \u25B8 {sr_name}", font=theme.font(14, "bold"),
                 fg="white", bg=bg, anchor="w").place(x=20, y=14, width=480, height=24)
        tk.Label(dlg, text="A member gets everything allowed for Everyone plus everything "
                           "allowed for each of their roles. The host and administrators "
                           "always have full access.",
                 font=theme.font(10, slant="italic"), fg=theme.SOFT_BLUE, bg=bg, anchor="w",
                 wraplength=480, justify="left").place(x=20, y=40, width=480, height=32)

        for i, head in enumerate(("Read", "Send", "Upload")):
            tk.Label(dlg, text=head, font=theme.font(9, "bold"), fg="#8ca5d2", bg=bg,
                     anchor="center").place(x=272 + i * 68, y=76, width=50, height=16)

        canvas = tk.Canvas(dlg, bg="#1c2a55", highlightthickness=1,
                           highlightbackground=theme.MEDIUM_BLUE)
        canvas.place(x=20, y=96, width=464, height=250)
        sb = tk.Scrollbar(dlg, orient="vertical", command=canvas.yview)
        sb.place(x=484, y=96, width=16, height=250)
        canvas.configure(yscrollcommand=sb.set)
        panel = tk.Frame(canvas, bg="#1c2a55")
        canvas.create_window((0, 0), window=panel, anchor="nw", width=462)
        panel.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        entries = []   # (role_id or None for Everyone, read, send, upload)

        def add_row(role_id, label, r, s, u, bold=False):
            f = tk.Frame(panel, bg="#1c2a55", height=34)
            f.pack(fill="x")
            f.pack_propagate(False)
            shown = label if len(label) <= 26 else label[:25] + "\u2026"
            tk.Label(f, text=shown, font=theme.font(11, "bold" if bold else "normal"),
                     fg="white", bg="#1c2a55", anchor="w").place(x=10, y=7, width=240, height=20)
            v_r, v_s, v_u = (tk.BooleanVar(value=bool(x)) for x in (r, s, u))

            def on_read():
                if not v_r.get():
                    v_s.set(False)
                    v_u.set(False)

            def on_write():
                if v_s.get() or v_u.get():
                    v_r.set(True)

            for i, (v, cmd) in enumerate(((v_r, on_read), (v_s, on_write), (v_u, on_write))):
                tk.Checkbutton(f, variable=v, command=cmd, bg="#1c2a55", fg="white",
                               selectcolor="#1c2a55", activebackground="#1c2a55",
                               activeforeground="white").place(x=262 + i * 68, y=5,
                                                                width=30, height=24)
            entries.append((role_id, v_r, v_s, v_u))

        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT everyone_read, everyone_send, everyone_upload "
                        "FROM room_sub_rooms WHERE sub_room_id=%s AND room_id=%s",
                        (sr_id, self.room_id))
            ev = cur.fetchone()
            cur.execute(
                "SELECT r.role_id, r.role_name, COALESCE(p.can_read,0) AS cr, "
                "COALESCE(p.can_send,0) AS cs, COALESCE(p.can_upload,0) AS cu "
                "FROM room_roles r LEFT JOIN sub_room_role_perms p "
                "ON p.role_id = r.role_id AND p.sub_room_id = %s "
                "WHERE r.room_id = %s ORDER BY r.role_name ASC", (sr_id, self.room_id))
            role_rows = cur.fetchall()
            cur.close()
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=dlg)
            close()
            return
        if not ev:
            close()
            return

        add_row(None, "Everyone (all members)", ev["everyone_read"], ev["everyone_send"],
                ev["everyone_upload"], bold=True)
        for r in role_rows:
            add_row(r["role_id"], r["role_name"], r["cr"], r["cs"], r["cu"])
        if not role_rows:
            tk.Label(panel, text='No custom roles yet. Create one with "Manage Roles".',
                     font=theme.font(10, slant="italic"), fg="#78a0c8",
                     bg="#1c2a55").pack(pady=14)

        status = tk.Label(dlg, text="", font=theme.font(10, "bold"), bg=bg, anchor="center")
        status.place(x=20, y=352, width=480, height=18)

        def do_save():
            if not self._is_host_or_admin():
                return
            try:
                conn = get_connection()
                cur = conn.cursor()
                for role_id, v_r, v_s, v_u in entries:
                    r_, s_, u_ = int(v_r.get()), int(v_s.get()), int(v_u.get())
                    if role_id is None:
                        cur.execute(
                            "UPDATE room_sub_rooms SET everyone_read=%s, everyone_send=%s, "
                            "everyone_upload=%s WHERE sub_room_id=%s AND room_id=%s",
                            (r_, s_, u_, sr_id, self.room_id))
                    else:
                        cur.execute(
                            "INSERT INTO sub_room_role_perms "
                            "(sub_room_id, role_id, can_read, can_send, can_upload) "
                            "VALUES (%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE "
                            "can_read=VALUES(can_read), can_send=VALUES(can_send), "
                            "can_upload=VALUES(can_upload)", (sr_id, role_id, r_, s_, u_))
                cur.close()
            except Exception as ex:
                status.configure(fg="#ff8080", text=f"Error: {ex}")
                return
            status.configure(fg="#50d250", text="\u2713 Saved")
            dlg.after(700, close)

        theme.make_button(dlg, "Save", theme.MEDIUM_BLUE, font_size=12,
                          command=do_save).place(x=110, y=382, width=130, height=36)
        theme.make_button(dlg, "Cancel", "#28376e", font_size=12,
                          command=close).place(x=280, y=382, width=130, height=36)

    def open_filtered_words_dialog(self):
        if self.current_sys_role not in ("professor", "admin"):
            return
        is_admin = self.current_sys_role == "admin"

        dlg = tk.Toplevel(self)
        dlg.title("Filtered Words")
        dlg.geometry("420x470")
        dlg.transient(self)
        dlg.grab_set()
        dlg.configure(bg=theme.SUB_ROOM_BG)
        dlg.resizable(False, False)

        tk.Label(dlg, text="Filtered Words", font=theme.font(14, "bold"), fg="white",
                 bg=theme.SUB_ROOM_BG, anchor="w").place(x=20, y=14, width=380, height=24)
        tk.Label(dlg, text=f"Messages containing these words are censored in {self.room_name}.",
                 font=theme.font(10, slant="italic"), fg=theme.SOFT_BLUE,
                 bg=theme.SUB_ROOM_BG, anchor="w", wraplength=380,
                 justify="left").place(x=20, y=40, width=380, height=30)

        lb = tk.Listbox(dlg, bg="#1c2a55", fg="white", font=theme.font(12),
                         selectbackground=theme.MEDIUM_BLUE, exportselection=False,
                         highlightthickness=1, highlightbackground=theme.MEDIUM_BLUE)
        lb.place(x=20, y=78, width=380, height=210)

        entries = []   # parallel to the listbox rows: (word_id, room_id)

        def load():
            lb.delete(0, tk.END)
            entries.clear()
            try:
                conn = get_connection()
                cur = conn.cursor(dictionary=True)
                cur.execute(
                    "SELECT word_id, room_id, word FROM filtered_words "
                    "WHERE room_id=%s OR room_id IS NULL "
                    "ORDER BY room_id IS NULL DESC, word ASC",
                    (self.room_id,),
                )
                for r in cur.fetchall():
                    scope = "  [ALL ROOMS]" if r["room_id"] is None else ""
                    lb.insert(tk.END, r["word"] + scope)
                    entries.append((r["word_id"], r["room_id"]))
                cur.close()
            except Exception as ex:
                status.configure(fg="#ff8080", text=f"Error: {ex}")

        status = tk.Label(dlg, text="", font=theme.font(10), bg=theme.SUB_ROOM_BG,
                          anchor="center")
        status.place(x=20, y=296, width=380, height=18)

        tf_word = tk.Entry(dlg, font=theme.font(12), bg="white", fg=theme.DARK_NAVY,
                            relief="solid", bd=1, highlightthickness=1,
                            highlightbackground=theme.SOFT_BLUE)
        tf_word.place(x=20, y=322, width=250, height=32)

        all_rooms_var = tk.BooleanVar(value=False)
        if is_admin:
            tk.Checkbutton(dlg, text="Apply to all rooms", variable=all_rooms_var,
                           font=theme.font(10), fg="white", bg=theme.SUB_ROOM_BG,
                           selectcolor=theme.SUB_ROOM_BG, activebackground=theme.SUB_ROOM_BG,
                           activeforeground="white").place(x=20, y=358, width=200, height=22)

        def do_add():
            scope = None if (is_admin and all_rooms_var.get()) else self.room_id
            ok, msg = add_filtered_word(tf_word.get(), scope, self.current_user_id)
            if ok:
                tf_word.delete(0, tk.END)
                status.configure(fg="#50d250", text="\u2713 Word added.")
                load()
            else:
                status.configure(fg="#ff8080", text=msg)

        def do_remove():
            sel = lb.curselection()
            if not sel:
                status.configure(fg="#ff8080", text="Select a word first.")
                return
            word_id, scope_room = entries[sel[0]]
            if scope_room is None and not is_admin:
                status.configure(fg="#ff8080", text="Only an administrator can remove global words.")
                return
            remove_filtered_word(word_id)
            status.configure(fg="#50d250", text="\u2713 Word removed.")
            load()

        theme.make_button(dlg, "Add", theme.MEDIUM_BLUE, font_size=11,
                          command=do_add).place(x=280, y=322, width=120, height=32)
        theme.make_button(dlg, "Remove Selected", theme.RED_ACCENT, font_size=11,
                          command=do_remove).place(x=20, y=392, width=180, height=34)
        theme.make_button(dlg, "Close", "#28376e", font_size=11,
                          command=dlg.destroy).place(x=280, y=392, width=120, height=34)
        tf_word.bind("<Return>", lambda e: do_add())

        load()

    # ═════════════════════════════════════════════════════════════════
    #  PERMISSION HELPERS
    # ═════════════════════════════════════════════════════════════════
    def save_member_perms(self, user_id, can_send, can_read, can_manage, can_post_announce=False):
        # only an admin may change a host's permissions; everyone else is limited to non-hosts
        try:
            conn = get_connection()
            cur = conn.cursor()
            sql = ("UPDATE room_members SET can_send_messages=%s, can_read_history=%s, "
                   "can_manage_members=%s, can_post_announcements=%s "
                   "WHERE room_id=%s AND user_id=%s")
            if self.current_sys_role != "admin":
                sql += " AND room_role != 'host'"
            cur.execute(sql, (int(can_send), int(can_read), int(can_manage),
                              int(can_post_announce), self.room_id, user_id))
            cur.close()
        except Exception as ex:
            print(f"save_member_perms error: {ex}")

    # ═════════════════════════════════════════════════════════════════
    #  SUB-ROOM CRUD
    # ═════════════════════════════════════════════════════════════════
    def add_sub_room(self, sr_name):
        """Returns the new sub-room's id, or None on error."""
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT COALESCE(MAX(position)+1, 0) FROM room_sub_rooms WHERE room_id=%s",
                (self.room_id,),
            )
            pos = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO room_sub_rooms (room_id, sub_room_name, sub_room_type, "
                "sub_room_type_detail, position) VALUES (%s,%s,'text','public',%s)",
                (self.room_id, sr_name, pos),
            )
            new_id = cur.lastrowid
            cur.close()
            return new_id
        except Exception as ex:
            messagebox.showerror("Error", f"Error adding sub-room: {ex}", parent=self)
            return None

    def delete_sub_room(self, sr_id):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM room_messages WHERE sub_room_id=%s", (sr_id,))
            cur.execute("DELETE FROM room_sub_rooms WHERE sub_room_id=%s", (sr_id,))
            cur.close()
        except Exception as ex:
            messagebox.showerror("Error", f"Error deleting sub-room: {ex}", parent=self)

    def delete_room(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM rooms WHERE room_id=%s", (self.room_id,))
            cur.close()
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)
            return
        self.stop_polling()
        self.destroy()
        self.parent_lobby.deiconify()
        self.parent_lobby.refresh_rooms()

    def _get_invite_code(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT invite_code FROM rooms WHERE room_id=%s", (self.room_id,))
            row = cur.fetchone()
            cur.close()
            if row:
                return row[0]
        except Exception:
            pass
        return "N/A"

    # ═════════════════════════════════════════════════════════════════
    #  POLLING
    # ═════════════════════════════════════════════════════════════════
    def _room_is_archived(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT is_archived FROM rooms WHERE room_id=%s", (self.room_id,))
            row = cur.fetchone()
            cur.close()
            return bool(row and row[0] == 1)
        except Exception:
            return False

    def set_room_archived(self, archived):
        """Host or admin only (checked in the query). Returns True if applied."""
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "UPDATE rooms SET is_archived=%s, archived_at=IF(%s=1, NOW(), NULL) "
                "WHERE room_id=%s AND (host_id=%s OR %s=1)",
                (int(archived), int(archived), self.room_id, self.current_user_id,
                 1 if self.current_sys_role == "admin" else 0),
            )
            ok = cur.rowcount > 0
            cur.close()
            return ok
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)
            return False

    def check_archived(self):
        """Members still inside a room that just got archived go back to the lobby.
        Returns True if this window was closed."""
        if self.current_sys_role == "admin" or self.my_room_role == "host":
            return False
        if not self._room_is_archived():
            return False
        messagebox.showinfo("Room archived",
                             "This room has been archived by its host.", parent=self)
        self.go_back()
        return True
    
    def start_polling(self):
        def tick():
            if self.check_archived():
                return
            self.load_sub_rooms()
            if self.selected_sub_room_id != -1:
                self.refresh_messages()
            self.load_members()
            self.apply_permissions_to_input()
            self.check_dm_preview()
            self.check_admin_alerts()
            self._polling_job = self.after(1500, tick)

        self._polling_job = self.after(1500, tick)

    def stop_polling(self):
        if self._polling_job is not None:
            try:
                self.after_cancel(self._polling_job)
            except Exception:
                pass
            self._polling_job = None

    def check_admin_alerts(self):
        is_admin = self.current_sys_role == "admin"
        if not is_admin and self.my_room_role != "host":
            return
        n = count_unread_alerts(self.current_user_id, is_admin)
        if n:
            self.btn_alerts.configure(text=f"\u26A0 {n} new alert(s)")
            self.btn_alerts.place(x=445, y=10, width=140, height=28)
        else:
            self.btn_alerts.place_forget()

    # ═════════════════════════════════════════════════════════════════
    #  NAVIGATION
    # ═════════════════════════════════════════════════════════════════
    def go_back(self):
        self.stop_polling()
        self.destroy()
        self.parent_lobby.deiconify()
        self.parent_lobby.refresh_rooms()

    def _logout(self):
        self.stop_polling()
        self.destroy()
        self.parent_lobby.destroy()
        from ui.login_frame import LoginFrame
        LoginFrame().mainloop()

    # ═════════════════════════════════════════════════════════════════
    #  SMALL HELPERS
    # ═════════════════════════════════════════════════════════════════
    def _display_name(self):
        return self.current_full_name or self.current_username

    def _dlg_sep(self, dlg, y):
        tk.Frame(dlg, bg=theme.MEDIUM_BLUE, height=2).place(x=20, y=y, width=520, height=2)

    def _center(self):
        self.update_idletasks()
        w, h = 1150, 750
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
