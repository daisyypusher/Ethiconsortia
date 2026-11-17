# Ethiconsortia

A school messaging app for announcements. Students, professors and administrators
chat in rooms and sub-rooms. There are no calls.

## Download

1. Open the [Releases page](https://github.com/daisyypusher/Ethiconsortia/releases).
2. Download `Ethiconsortia.exe` from the newest release.
3. Double-click it. Windows may show a blue "Windows protected your PC" box
   because the app is not signed. Click **More info**, then **Run anyway**.

No Python is needed. Windows 10 or 11 only.

## First run: connect to the database

The first time you open the app it asks for the database login.
You must be on the same network as the database computer.

| Field | Value |
|---|---|
| Server address (host) | `<YOUR_IPv4 address>` |
| Port | `3306` |
| Database name | `ethiconsortia` |
| Database user | `ethic_app` |
| Database password | `connect` |

Click **TEST CONNECTION**. When it says "Connected", click **SAVE & CONTINUE**.
You can change these later with **Database settings** on the login screen.

## Create an account

Click **CREATE AN ACCOUNT** on the login screen.

- **Student:** no code needed.
- **Professor / Administrator:** you need an access code. Ask your administrator.

## Using the app

- **Create Room** makes you the host. Share the invite code so others can join.
- **Join Room** asks for an invite code.
- Each room has sub-rooms (channels). Open the gear icon (host or administrator)
  to manage permissions, roles and sub-rooms.
- Messages cannot be deleted. You can edit a message, and everyone can see the
  edit history.
- Tag your own messages as Announcement, Question, Emergency, Wrong sent or Other.

## For the person hosting the database

1. Install MySQL or MariaDB (XAMPP works).
2. Create a database named `ethiconsortia` and import `ethiconsortia.sql`.
3. Create the user `ethic_app` and give it rights on that database only.
4. Allow connections from other computers: do not bind MySQL to `127.0.0.1` only,
   and open port 3306 in Windows Firewall.
5. Add access codes for professors and administrators to the `verification_codes` table.

## Build from source

    pip install -r requirements.txt
    python main.py

Releases are built automatically when a tag like `v1.0.0` is pushed.