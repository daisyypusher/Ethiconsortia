"""
ui/chat_frame.py
─────────────────────────────────────────────────────────────
"""
import tkinter as tk
from tkinter import messagebox

from db.connection import get_connection
from ui import theme, emote_picker, image_message_handler as imh

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


class ChatFrame(tk.Tk):
    def __init__(self, user_id, username, full_name, role):
        super().__init__()
        self.current_user_id = user_id
        self.current_username = username
        self.current_full_name = full_name
        self.current_role = role
        self.selected_receiver_id = -1
        self.selected_receiver_name = ""
        self.username_to_id = {}
        self._img_refs = []

        self.title(f"Ethiconsortia \u2014 {theme.role_badge(role)} {full_name}")
        self.geometry("1100x750")
        self.resizable(False, False)
        self.configure(bg=theme.DARK_NAVY)

        main = tk.Frame(self, bg=theme.DARK_NAVY)
        main.place(x=0, y=0, width=1100, height=620)

        icon_sidebar = self._build_icon_sidebar(main)
        contacts_panel = self._build_contacts_panel(main)
        chat_panel = self._build_chat_panel(main)
        right_panel = self._build_right_panel(main)

        icon_sidebar.place(x=0, y=0, width=65, height=620)
        contacts_panel.place(x=65, y=0, width=220, height=620)
        chat_panel.place(x=285, y=0, width=580, height=620)
        right_panel.place(x=865, y=0, width=235, height=620)

        self.load_users()
        self.start_polling()

    # ── LEFT ICON SIDEBAR ──
    def _build_icon_sidebar(self, parent):
        p = tk.Frame(parent, bg=theme.DARK_NAVY)
        tk.Label(p, text="E", font=theme.font(22, "bold"), fg="white",
                 bg=theme.DARK_NAVY, anchor="center").place(x=0, y=10, width=65, height=40)
        tk.Label(p, text="\U0001F464", font=theme.font(20, emoji=True), fg="white",
                 bg=theme.MEDIUM_BLUE, anchor="center").place(x=10, y=60, width=45, height=45)
        for y in (120, 175, 230):
            tk.Label(p, text="\U0001F3DB", font=theme.font(18, emoji=True), fg="white",
                     bg=theme.MEDIUM_BLUE, anchor="center").place(x=10, y=y, width=45, height=45)

        tk.Label(p, text="+", font=theme.font(18, "bold"), fg="white", bg=theme.RED_ACCENT,
                 anchor="center").place(x=15, y=290, width=35, height=35)
        tk.Label(p, text=theme.role_badge(self.current_role), font=theme.font(7, "bold"),
                 fg=theme.SOFT_BLUE, bg=theme.DARK_NAVY,
                 anchor="center").place(x=0, y=340, width=65, height=15)

        btn_logout = theme.make_button(p, "Logout", theme.RED_ACCENT, font_size=8,
                                        command=self._logout)
        btn_logout.place(x=5, y=545, width=55, height=25)
        btn_settings = theme.make_button(p, "Settings", "#283c6e", font_size=8,
                                          command=lambda: None)
        btn_settings.place(x=5, y=575, width=55, height=25)
        return p

    def _logout(self):
        self.stop_polling()
        self.destroy()
        from ui.login_frame import LoginFrame
        LoginFrame().mainloop()

    # ── CONTACTS PANEL ──
    def _build_contacts_panel(self, parent):
        p = tk.Frame(parent, bg=theme.MEDIUM_BLUE)
        tk.Label(p, text="\U0001F464", font=theme.font(28, emoji=True),
                 bg=theme.MEDIUM_BLUE).place(x=10, y=10, width=45, height=45)
        name = self.current_full_name or self.current_username
        tk.Label(p, text=name, font=theme.font(12, "bold"), fg="white", bg=theme.MEDIUM_BLUE,
                 anchor="w").place(x=65, y=12, width=148, height=18)
        tk.Label(p, text=theme.role_badge(self.current_role), font=theme.font(9, "bold"),
                 fg="white", bg=theme.role_color(self.current_role),
                 anchor="center").place(x=65, y=33, width=80, height=16)

        tk.Frame(p, bg=theme.SOFT_BLUE, height=2).place(x=0, y=65, width=220, height=2)
        tk.Label(p, text="CONTACTS", font=theme.font(11, "bold"), fg=theme.RED_ACCENT,
                 bg=theme.MEDIUM_BLUE, anchor="w").place(x=10, y=73, width=200, height=18)

        listbox_frame = tk.Frame(p)
        listbox_frame.place(x=5, y=93, width=210, height=200)
        self.contact_listbox = tk.Listbox(listbox_frame, bg=theme.MEDIUM_BLUE, fg="white",
                                           font=theme.font(10), selectbackground=theme.DARK_NAVY,
                                           highlightthickness=0, bd=0)
        self.contact_listbox.pack(fill="both", expand=True)
        self.contact_listbox.bind("<<ListboxSelect>>", self._on_contact_select)

        tk.Label(p, text="SUB-ROOMS", font=theme.font(11, "bold"), fg=theme.RED_ACCENT,
                 bg=theme.MEDIUM_BLUE, anchor="w").place(x=10, y=305, width=200, height=18)

        sub_rooms = [("\U0001F4E2", "ANNOUNCEMENTS", "news, events, seminars, etc..."),
                     ("#", "MAIN", "activities, projects, etc..."),
                     ("#", "STUDENT BOARD", "anonymous discussions")]
        cy = 328
        for icon, sr_name, desc in sub_rooms:
            item = tk.Frame(p, bg=theme.MEDIUM_BLUE, cursor="hand2")
            item.place(x=5, y=cy, width=210, height=55)
            tk.Label(item, text=icon, font=theme.font(15, emoji=True), fg="white",
                     bg=theme.DARK_NAVY, anchor="center").place(x=0, y=5, width=34, height=40)
            tk.Label(item, text=sr_name, font=theme.font(10, "bold"), fg="white",
                     bg=theme.MEDIUM_BLUE, anchor="w").place(x=40, y=5, width=165, height=18)
            tk.Label(item, text=desc, font=theme.font(9, slant="italic"), fg=theme.SOFT_BLUE,
                     bg=theme.MEDIUM_BLUE, anchor="w").place(x=40, y=24, width=165, height=14)
            cy += 60

        return p

    def _on_contact_select(self, _e=None):
        sel = self.contact_listbox.curselection()
        if not sel:
            return
        name = self.contact_listbox.get(sel[0])
        self.selected_receiver_name = name
        self.selected_receiver_id = self.username_to_id.get(name, -1)
        self.lbl_sub_room_name.configure(text=name.upper())
        self.lbl_sub_room_type.configure(text="DIRECT MESSAGE")
        self.lbl_right_title.configure(text=name.upper())
        self.refresh_messages()

    # ── CHAT PANEL ──
    def _build_chat_panel(self, parent):
        p = tk.Frame(parent, bg=theme.CHAT_BG)
        top_bar = tk.Frame(p, bg="#c8d7f5")
        top_bar.place(x=0, y=0, width=580, height=50)
        self.lbl_sub_room_name = tk.Label(top_bar, text="Select a Contact",
                                           font=theme.font(14, "bold"), fg=theme.DARK_NAVY,
                                           bg="#c8d7f5", anchor="w")
        self.lbl_sub_room_name.place(x=15, y=5, width=450, height=22)
        self.lbl_sub_room_type = tk.Label(top_bar, text="", font=theme.font(10),
                                           fg=theme.MEDIUM_BLUE, bg="#c8d7f5", anchor="w")
        self.lbl_sub_room_type.place(x=15, y=28, width=450, height=16)

        canvas = tk.Canvas(p, bg=theme.CHAT_BG, highlightthickness=0)
        canvas.place(x=0, y=50, width=580, height=450)
        self.chat_messages_panel = tk.Frame(canvas, bg=theme.CHAT_BG)
        canvas.create_window((0, 0), window=self.chat_messages_panel, anchor="nw", width=580)
        self.chat_messages_panel.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self._chat_canvas = canvas

        input_bar = tk.Frame(p, bg="#e1e8f8")
        input_bar.place(x=0, y=500, width=580, height=60)

        btn_image = tk.Button(input_bar, text="\U0001F5BC", font=theme.font(16, emoji=True),
                               bg="#e1e8f8", relief="flat", bd=0, cursor="hand2",
                               command=self.open_image_chooser)
        btn_image.place(x=8, y=13, width=36, height=32)

        btn_emoji = tk.Button(input_bar, text="\U0001F60A", font=theme.font(16, emoji=True),
                               bg="#e1e8f8", relief="flat", bd=0, cursor="hand2")
        btn_emoji.place(x=50, y=13, width=36, height=32)
        btn_emoji.configure(command=lambda: emote_picker.show(btn_emoji, self.send_emote))

        self.txt_message = tk.Entry(input_bar, font=theme.font(12), fg="gray", bg="white",
                                     relief="solid", bd=1)
        self.txt_message.insert(0, "Type a message...")
        self.txt_message.place(x=94, y=12, width=352, height=34)

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

        btn_send = theme.make_button(input_bar, "\u27a4", theme.DARK_NAVY, font_size=14,
                                      command=self.send_message)
        btn_send.place(x=453, y=12, width=120, height=34)

        p.add = lambda *a, **k: None  # placeholder no-op to mirror original naming
        return p

    def send_emote(self, emote):
        self._send_raw(emote, "emote")

    def open_image_chooser(self):
        if self.selected_receiver_id == -1:
            messagebox.showinfo("Info", "Please select a contact first.", parent=self)
            return
        path = imh.choose_image_file(self)
        if not path:
            return
        b64 = imh.file_to_base64_raw(path)
        mime = imh.guess_mime(path)
        self._send_raw(f"{mime}|{b64}", "image")

    def _dm_sub_room_id(self):
        """Return the room_sub_rooms.sub_room_id for the DM pair
        (current_user, selected_receiver). Creates it if missing."""
        a, b = sorted((self.current_user_id, self.selected_receiver_id))
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT sub_room_id FROM room_sub_rooms
            WHERE sub_room_type_detail = 'private'
              AND dm_user_a = %s AND dm_user_b = %s
            LIMIT 1
            """,
            (a, b),
        )
        row = cur.fetchone()
        if row:
            cur.close()
            return row["sub_room_id"]
        cur.execute(
            """
            INSERT INTO room_sub_rooms
                (room_id, sub_room_name, sub_room_type, position,
                 sub_room_type_detail, dm_user_a, dm_user_b)
            VALUES (1, %s, 'text', 0, 'private', %s, %s)
            """,
            (f"dm-{a}-{b}", a, b),
        )
        new_id = cur.lastrowid
        cur.close()
        return new_id

    def _send_raw(self, content, msg_type):
        if self.selected_receiver_id == -1:
            messagebox.showinfo("Info", "Please select a contact first.", parent=self)
            return
        # For images, `content` is "mime|base64". Move it to image_data and
        # leave `content` empty.
        if msg_type == "image":
            image_data = content
            text_content = ""
        else:
            image_data = None
            text_content = content

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO room_messages
                    (sub_room_id, sender_id, receiver_id, content,
                     msg_type, is_private, image_data)
                VALUES (%s,%s,%s,%s,%s,1,%s)
                """,
                (self._dm_sub_room_id(), self.current_user_id,
                 self.selected_receiver_id, text_content, msg_type,
                 image_data),
            )
            cur.close()
            self.refresh_messages()
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)

    # ── RIGHT PANEL ──
    def _build_right_panel(self, parent):
        p = tk.Frame(parent, bg=theme.RIGHT_BG)
        tk.Label(p, text="\U0001F3DB", font=theme.font(38, emoji=True),
                 bg=theme.RIGHT_BG, anchor="center").place(x=75, y=10, width=80, height=75)
        self.lbl_right_title = tk.Label(p, text="SELECT A CHAT", font=theme.font(12, "bold"),
                                         fg=theme.DARK_NAVY, bg=theme.RIGHT_BG, anchor="center")
        self.lbl_right_title.place(x=5, y=90, width=225, height=22)

        search = tk.Entry(p, font=theme.font(11), fg="gray", relief="solid", bd=1)
        search.insert(0, "Search...")
        search.place(x=10, y=120, width=215, height=28)

        tk.Label(p, text="COURSE DESCRIPTION", font=theme.font(10, "bold"), fg=theme.RED_ACCENT,
                 bg=theme.RIGHT_BG, anchor="w").place(x=10, y=158, width=215, height=18)

        desc = ("This programming course is a continuation of the foundational skill of all "
                "computing discipline.\n\nThe course will focus on skills that enable learners "
                "to design, test, implement and debug problems intended to solve computing "
                "problems using basic data structures and standard libraries.")
        tk.Label(p, text=desc, font=theme.font(10), fg=theme.DARK_NAVY, bg=theme.RIGHT_BG,
                 wraplength=205, justify="left", anchor="nw").place(x=10, y=178, width=215, height=125)

        tk.Label(p, text="Chat members", font=theme.font(11, "bold"), fg=theme.DARK_NAVY,
                 bg=theme.RIGHT_BG, anchor="w").place(x=10, y=310, width=215, height=18)

        canvas = tk.Canvas(p, bg=theme.RIGHT_BG, highlightthickness=0)
        canvas.place(x=5, y=330, width=225, height=270)
        self.right_members_panel = tk.Frame(canvas, bg=theme.RIGHT_BG)
        canvas.create_window((0, 0), window=self.right_members_panel, anchor="nw", width=225)
        self.right_members_panel.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        self.load_members_list()
        return p

    def load_members_list(self):
        for w in self.right_members_panel.winfo_children():
            w.destroy()
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT full_name, username, role FROM users ORDER BY role, full_name")
            for r in cur.fetchall():
                self._add_member(r["full_name"] or r["username"], r["role"])
            cur.close()
        except Exception:
            self._add_member("Error loading", "student")

    def _add_member(self, name, role):
        mp = tk.Frame(self.right_members_panel, bg=theme.RIGHT_BG)
        mp.pack(fill="x", pady=2, padx=5, anchor="w")
        emoji = {"professor": "\U0001F468\u200D\U0001F3EB", "admin": "\U0001F6E1"}.get(role, "\U0001F464")
        tk.Label(mp, text=emoji, font=theme.font(13, emoji=True), bg=theme.RIGHT_BG).pack(side="left")
        tk.Label(mp, text=f"{theme.role_label(role)} ", font=theme.font(9), fg=theme.role_color(role),
                 bg=theme.RIGHT_BG).pack(side="left")
        tk.Label(mp, text=name, font=theme.font(9, "bold"), fg=theme.DARK_NAVY,
                 bg=theme.RIGHT_BG).pack(side="left")

    # ── MESSAGES ──
    def refresh_messages(self):
        if self.selected_receiver_id == -1:
            return
        for w in self.chat_messages_panel.winfo_children():
            w.destroy()
        self._img_refs.clear()

        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT u.username AS sender, m.content, m.sent_at,
                       COALESCE(m.msg_type, 'text') AS msg_type,
                       m.image_data, m.is_read
                FROM room_messages m
                JOIN users u ON m.sender_id = u.user_id
                WHERE m.is_private = 1
                  AND ((m.sender_id=%s AND m.receiver_id=%s)
                    OR (m.sender_id=%s AND m.receiver_id=%s))
                ORDER BY m.sent_at ASC
                """,
                (self.current_user_id, self.selected_receiver_id,
                 self.selected_receiver_id, self.current_user_id),
            )
            for r in cur.fetchall():
                is_me = r["sender"] == self.current_username
                time_str = r["sent_at"].strftime("%Y-%m-%d %H:%M")
                bubble = self._make_bubble(
                    r["content"], time_str, is_me, r["msg_type"],
                    image_data=r.get("image_data"),
                )
                bubble.pack(fill="x", pady=(0, 6))
            cur.close()
        except Exception as ex:
            print(f"Error: {ex}")

        self.after(50, lambda: self._chat_canvas.yview_moveto(1.0))

    def _make_bubble(self, content, time_str, is_me, msg_type, image_data=None):
        outer = tk.Frame(self.chat_messages_panel, bg=theme.CHAT_BG)
        holder = tk.Frame(outer, bg=theme.CHAT_BG)
        holder.pack(side="right" if is_me else "left", padx=8)

        bubble_bg = theme.MSG_YOU_BG if is_me else theme.MSG_THEM_BG
        bubble = tk.Frame(holder, bg=bubble_bg)
        avatar = tk.Label(holder, text="\U0001F464", font=theme.font(20, emoji=True), bg=theme.CHAT_BG)

        tk.Label(bubble, text="YOU" if is_me else "THEM", font=theme.font(8, "bold"),
                 fg=theme.MEDIUM_BLUE, bg=bubble_bg, anchor="w").pack(fill="x", padx=12, pady=(7, 0))

        if msg_type == "image":
            payload = image_data or content   # fallback for old rows
            img = imh.decode_base64_image(payload) if payload else None
            if img:
                photo = imh.make_photo(img, 260, 200)
                self._img_refs.append(photo)
                lbl = tk.Label(bubble, image=photo, bg=bubble_bg, cursor="hand2")
                lbl.pack(padx=12, pady=4)
                lbl.bind("<Button-1>", lambda e, im=img: imh.show_full_image(self, im))
            else:
                tk.Label(bubble, text="[Image could not be displayed]",
                         bg=bubble_bg).pack(padx=12, pady=4)
        elif msg_type == "emote":
            tk.Label(bubble, text=content, font=theme.font(38, emoji=True), bg=bubble_bg).pack(
                padx=12, pady=4)
        else:
            tk.Label(bubble, text=content, font=theme.font(12), fg=theme.DARK_NAVY, bg=bubble_bg,
                     wraplength=320, justify="left", anchor="w").pack(fill="x", padx=12, pady=4)

        tk.Label(bubble, text=time_str, font=theme.font(8), fg="gray", bg=bubble_bg,
                 anchor="w").pack(fill="x", padx=12, pady=(0, 7))

        if is_me:
            bubble.pack(side="left")
            avatar.pack(side="left")
        else:
            avatar.pack(side="left")
            bubble.pack(side="left")
        return outer

    def send_message(self):
        content = self.txt_message.get().strip()
        if not content or content == "Type a message...":
            return
        if self.selected_receiver_id == -1:
            messagebox.showinfo("Info", "Please select a contact first.", parent=self)
            return
        self._send_raw(content, "text")
        self.txt_message.delete(0, tk.END)
        if self.focus_get() is self.txt_message:
            self.txt_message.configure(fg=theme.DARK_NAVY)
        else:
            self.txt_message.insert(0, "Type a message...")
            self.txt_message.configure(fg="gray")

    def load_users(self):
        try:
            conn = get_connection()
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT user_id, username FROM users WHERE user_id != %s",
                        (self.current_user_id,))
            self.contact_listbox.delete(0, tk.END)
            self.username_to_id.clear()
            for r in cur.fetchall():
                self.contact_listbox.insert(tk.END, r["username"])
                self.username_to_id[r["username"]] = r["user_id"]
            cur.close()
        except Exception as ex:
            print(f"Error loading users: {ex}")

    def start_polling(self):
        def tick():
            if self.selected_receiver_id != -1:
                self.refresh_messages()
            self._polling_job = self.after(2000, tick)
        self._polling_job = self.after(2000, tick)

    def stop_polling(self):
        job = getattr(self, "_polling_job", None)
        if job is not None:
            try:
                self.after_cancel(job)
            except Exception:
                pass


if __name__ == "__main__":
    # Standalone test launch — normally reached only via a custom entry point,
    # since the live app flow never opens ChatFrame (see note above).
    ChatFrame(1, "Jed", "Maurish Jed Igloso", "student").mainloop()
