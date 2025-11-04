# MMDVMHost → LCDproc Virtual Display API Specification

*Version 1.0 (Draft)*  
*Last updated 2025-11-04*

---

## 1  Overview
This document defines the protocol and data model used when **MMDVMHost** connects to a **virtual LCDproc display server**.  
It allows implementers to replace the physical LCD (via LCDd) with a networked process or web dashboard that receives and renders text updates in real time.

---

## 2  Transport
| Property | Value |
|-----------|-------|
| **Protocol** | TCP |
| **Default port** | `13666` |
| **Encoding** | UTF-8 text |
| **Framing** | One command per line (`\n` newline) |
| **Directionality** | Client = MMDVMHost → Server = Display |

---

## 3  Connection Lifecycle
### 3.1  Server Greeting
Immediately after connect, the server sends:

```
connect LCDproc <server_version> protocol <protocol_version> lcd wid <W> hgt <H> cellwid <cw> cellhgt <ch>
```
Example  
```
connect LCDproc 0.5.9 protocol 0.3.1 lcd wid 20 hgt 4 cellwid 5 cellhgt 8
```

### 3.2  Client Handshake
Typical sequence:
```
hello
client_set name MMDVMHost
screen_add scr1
screen_set scr1 -name "MMDVM" -heartbeat off -backlight on
widget_add scr1 l1 string
widget_add scr1 l2 string
widget_add scr1 l3 string
widget_add scr1 l4 string
```

Each command should be acknowledged with:
```
success
```

### 3.3  Operational Phase
MMDVMHost issues repeated updates:
```
widget_set scr1 l1 1 1 "DMR  →  BM 3120"
widget_set scr1 l2 1 2 "Call: N0CALL"
widget_set scr1 l3 1 3 "TG: 3120  Slot: 2"
widget_set scr1 l4 1 4 "Timer: 00:12  RSSI"
```

Optional keep-alive:
```
noop
```

### 3.4  Termination
```
bye
```
Server replies `success` and may close the socket.

---

## 4  Supported Commands
| Command | Direction | Description | Response |
|----------|------------|--------------|-----------|
| `hello` | C → S | Initial hello | `success` |
| `client_set name <NAME>` | C → S | Identify client | `success` |
| `screen_add <SCR>` | C → S | Create logical screen | `success` |
| `screen_set <SCR> [flags]` | C → S | Update screen metadata (`-name`, `-priority`, etc.) | `success` |
| `screen_del <SCR>` | C → S | Remove screen | `success` |
| `widget_add <SCR> <WID> string` | C → S | Add text widget | `success` |
| `widget_set <SCR> <WID> <X> <Y> "<TEXT>"` | C → S | Update widget position/text | `success` |
| `widget_del <SCR> <WID>` | C → S | Remove widget | `success` |
| `noop` | C → S | Keep-alive | `success` |
| `bye` | C → S | End session | `success` |

Any unrecognized command → `huh?`

---

## 5  Coordinate System and Text Rules
- **1-based coordinates:** `(1,1)` = top-left.  
- **Clamp/truncate** text to fit within declared width × height.  
- **Strings** are quoted; allow escaped quotes (`\"`).  
- Only widget type `string` is required for MMDVMHost compatibility.

---

## 6  Server State Model
```jsonc
{
  "screens": {
    "scr1": {
      "name": "MMDVM",
      "priority": 5,
      "widgets": {
        "l1": {"type":"string","x":1,"y":1,"text":"DMR  →  BM 3120"},
        "l2": {"type":"string","x":1,"y":2,"text":"Call: N0CALL"},
        "l3": {"type":"string","x":1,"y":3,"text":"TG: 3120  Slot: 2"},
        "l4": {"type":"string","x":1,"y":4,"text":"Timer: 00:12  RSSI"}
      }
    }
  },
  "active_screen": "scr1",
  "display": [
    "DMR  →  BM 3120     ",
    "Call: N0CALL        ",
    "TG: 3120  Slot: 2   ",
    "Timer: 00:12  RSSI  "
  ]
}
```

---

## 7  Normalized Event Schema
Your virtual display may emit structured events for web or MQTT subscribers.

### 7.1  Envelope
```json
{
  "ts": "2025-11-04T13:21:45.123Z",
  "type": "WidgetUpdated",
  "data": { ... }
}
```

### 7.2  Event Types
| Type | Data Fields |
|------|-------------|
| `ScreenCreated` | `{ "scr": "scr1", "name": "MMDVM", "priority": 5 }` |
| `ScreenUpdated` | `{ "scr": "scr1", "name": "...", "priority": 1 }` |
| `ScreenDeleted` | `{ "scr": "scr1" }` |
| `WidgetAdded` | `{ "scr": "scr1", "wid": "l1", "type": "string", "x":1, "y":1, "text":"" }` |
| `WidgetUpdated` | `{ "scr": "scr1", "wid": "l1", "x":1, "y":1, "text":"DMR  →  BM 3120" }` |
| `WidgetDeleted` | `{ "scr": "scr1", "wid": "l3" }` |
| `FrameRendered` | `{ "w":20,"h":4,"active_screen":"scr1","lines":["…"] }` |

---

## 8  Error Handling
- Unknown command → `huh?`
- Out-of-range coordinates → clamp safely.
- Missing screens/widgets → auto-create (lenient mode).
- Multiple screens → pick active by most recent or lowest priority.
- Ignore cosmetic flags (`heartbeat`, `backlight`) unless desired.

---

## 9  Security & Operational Notes
- Default bind: `127.0.0.1:13666`
- No authentication in protocol — firewall required if exposed.
- Low bandwidth: a few hundred bytes / second at most.
- Keep logs bounded (e.g., 500 entries).

---

## 10  Extensibility
- Add more widget types (`hbar`, `vbar`, `frame`) as needed.
- Expose raw lines as debug stream.
- Optional capability hint in greeting:
  ```
  connect LCDproc 0.5.9 protocol 0.3.1 lcd wid 20 hgt 4 cellwid 5 cellhgt 8 caps string-only
  ```

---

## 11  Server Conformance Checklist
- [ ] Send greeting line on connect  
- [ ] Respond `success` / `huh?` appropriately  
- [ ] Maintain in-memory state model  
- [ ] Render active screen text buffer  
- [ ] Expose `/state` or event API for dashboards  
- [ ] Never terminate on malformed input  

---

## 12  Example Wire Session
```
S→C: connect LCDproc 0.5.9 protocol 0.3.1 lcd wid 20 hgt 4 cellwid 5 cellhgt 8
C→S: hello
S→C: success
C→S: client_set name MMDVMHost
S→C: success
C→S: screen_add scr1
S→C: success
C→S: widget_add scr1 l1 string
S→C: success
C→S: widget_set scr1 l1 1 1 "YSF  →  US-Kansas"
S→C: success
...
C→S: bye
S→C: success
```

---

## 13  Reference Implementation
- **LCD Stub Server:** `lcd_stub.py` (Python 3, no deps)  
- **Dashboard:** `index.html` (polls `/state` @ 500 ms)

These conform fully to this spec and can be used for testing or integration templates.

---

### Authors
Specification derived from practical analysis of  
**G4KLX / MMDVMHost** and its LCDproc client behavior, 2025.
