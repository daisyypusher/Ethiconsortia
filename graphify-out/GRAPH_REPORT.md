# Graph Report - ethiconsortia_py  (2026-11-13)

## Corpus Check
- 16 files · ~20,522 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 1 file(s) not represented in the graph (top: (none) 1)

## Summary
- 366 nodes · 916 edges · 13 communities (10 shown, 3 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 61 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `32e99bae`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- RoomFrame
- get_connection
- image_message_handler.py
- RoomLobbyFrame
- font
- theme.py
- LoginFrame
- .open_roles_dialog
- load
- show
- message.py

## God Nodes (most connected - your core abstractions)
1. `get_connection()` - 88 edges
2. `RoomFrame` - 72 edges
3. `font()` - 58 edges
4. `RoomLobbyFrame` - 31 edges
5. `make_button()` - 25 edges
6. `ChatFrame` - 21 edges
7. `LoginFrame` - 20 edges
8. `is_banned()` - 17 edges
9. `is_locked_out()` - 13 edges
10. `RegisterFrame` - 13 edges

## Surprising Connections (you probably didn't know these)
- `get_warn_count()` --calls--> `get_connection()`  [EXTRACTED]
  ui/moderation_filter.py → db/connection.py
- `do_assign()` --calls--> `get_connection()`  [EXTRACTED]
  ui/room_frame.py → db/connection.py
- `do_save()` --calls--> `get_connection()`  [EXTRACTED]
  ui/room_frame.py → db/connection.py
- `load()` --calls--> `get_connection()`  [EXTRACTED]
  ui/room_frame.py → db/connection.py
- `do_create()` --calls--> `get_connection()`  [EXTRACTED]
  ui/room_frame.py → db/connection.py

## Import Cycles
- None detected.

## Communities (13 total, 3 thin omitted)

### Community 0 - "RoomFrame"
Cohesion: 0.05
Nodes (11): RoomFrame, on_click(), do_assign(), do_add(), do_delete_room(), do_save(), do_toggle_archive(), refresh_list() (+3 more)

### Community 1 - "get_connection"
Cohesion: 0.07
Nodes (27): get_connection(), add_filtered_word(), ban_in_department(), ban_user(), count_unread_alerts(), filter_message(), FilterResult, find_suspicious() (+19 more)

### Community 2 - "image_message_handler.py"
Cohesion: 0.06
Nodes (15): cursor(), choose_attachment(), choose_image_file(), decode_attachment(), decode_base64_image(), encode_attachment(), file_to_base64(), file_to_base64_raw() (+7 more)

### Community 3 - "RoomLobbyFrame"
Cohesion: 0.08
Nodes (16): RoomLobbyFrame, enter(), on_click(), do_restore(), load(), make_open(), _open(), do_create() (+8 more)

### Community 4 - "font"
Cohesion: 0.09
Nodes (9): open_tag_menu(), start_chat(), do_add(), do_remove(), load(), add_hover(), font(), make_button() (+1 more)

### Community 5 - "theme.py"
Cohesion: 0.11
Nodes (8): ChatFrame, tick(), fmt_datetime(), fmt_time(), role_badge(), role_color(), role_emoji(), role_label()

### Community 6 - "LoginFrame"
Cohesion: 0.11
Nodes (5): main(), LoginFrame, RegisterFrame, add_password_toggle(), entry_value()

### Community 7 - ".open_roles_dialog"
Cohesion: 0.25
Nodes (11): add_row(), do_save(), close(), do_create(), do_delete(), do_rename(), load_people(), load_roles() (+3 more)

### Community 8 - "load"
Cohesion: 0.50
Nodes (7): current_dept(), load(), make_ban(), _ban(), make_kick(), _kick(), say()

### Community 9 - "show"
Cohesion: 0.33
Nodes (3): show(), on_search_change(), show_card()

## Knowledge Gaps
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_connection()` connect `get_connection` to `RoomFrame`, `image_message_handler.py`, `RoomLobbyFrame`, `font`, `theme.py`, `LoginFrame`, `.open_roles_dialog`?**
  _High betweenness centrality (0.291) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `RoomFrame` (e.g. with `LoginFrame` and `RoomLobbyFrame`) actually correct?**
  _`RoomFrame` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `RoomFrame` be split into smaller, more focused modules?**
  _Cohesion score 0.05271629778672032 - nodes in this community are weakly interconnected._
- **Why does `RoomFrame` connect `RoomFrame` to `get_connection`, `image_message_handler.py`, `RoomLobbyFrame`, `font`, `LoginFrame`, `.open_roles_dialog`?**
  _High betweenness centrality (0.214) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `RoomLobbyFrame` (e.g. with `LoginFrame` and `RoomFrame`) actually correct?**
  _`RoomLobbyFrame` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Should `get_connection` be split into smaller, more focused modules?**
  _Cohesion score 0.07297726070861978 - nodes in this community are weakly interconnected._
- **Why does `font()` connect `font` to `RoomFrame`, `get_connection`, `image_message_handler.py`, `RoomLobbyFrame`, `theme.py`, `LoginFrame`, `.open_roles_dialog`, `load`, `show`?**
  _High betweenness centrality (0.175) - this node is a cross-community bridge._