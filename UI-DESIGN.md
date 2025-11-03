# UI Design Specification

**Design Philosophy:** Minimal aesthetics, maximum information density, optimized for small screens and dark mode.

---

## Color Scheme

### Mode Colors
Each digital mode has a distinct color for instant recognition:

| Mode | Color | Hex Code | Usage |
|------|-------|----------|-------|
| **DMR** | Green | `#00ff00` | DMR transmissions, DMR network status |
| **D-Star** | Cyan | `#00ffff` | D-Star transmissions, D-Star network |
| **YSF** | Yellow | `#ffff00` | System Fusion transmissions/network |
| **P25** | Orange | `#ff8800` | P25 transmissions, P25 network |
| **NXDN** | Magenta | `#ff00ff` | NXDN transmissions, NXDN network |
| **FM** | White | `#ffffff` | FM analog transmissions |
| **POCSAG** | Light Blue | `#8888ff` | POCSAG pager traffic |
| **SYSTEM** | Gray | `#888888` | System messages, errors, non-mode specific |

### Log Level Colors
Overlays on mode colors for warnings/errors:

| Level | Color | Hex Code | Usage |
|-------|-------|----------|-------|
| **ERROR** | Red | `#ff0000` | Fatal errors, failures |
| **WARN** | Orange | `#ffaa00` | Warnings, potential issues |
| **INFO** | White | `#ffffff` | Normal operation (default) |

### Status Indicator Colors

| Status | Color | Hex Code | Usage |
|--------|-------|----------|-------|
| **Active** | Green | `#00ff00` | Currently transmitting |
| **Idle** | Blue | `#0088ff` | Enabled, waiting for traffic |
| **Connected** | Cyan | `#00ffff` | Network connected |
| **Disconnected** | Red | `#ff0000` | Network offline |
| **Disabled** | Dark Gray | `#333333` | Mode disabled in config |

---

## Status Cards

### Mode Cards
Display current state of each configured digital mode.

**Layout:**
```
┌─────────────────────────────┐
│ [Icon] MODE NAME            │
│ Status: [Indicator]         │
│ Last Activity: 2m ago       │
│ Total Today: 42 QSOs        │
└─────────────────────────────┘
```

**States:**
- **Active (Green):** Currently receiving/transmitting
- **Idle (Blue):** Enabled, no current traffic
- **Disabled (Dark Gray):** Not configured in MMDVM.ini

**Example:**
```
┌─────────────────────────────┐
│ 📡 DMR Slot 1               │
│ Status: ● Active            │  ← Green dot
│ Last: KC1XXX → TG 31665     │
│ Activity: 15s ago           │
└─────────────────────────────┘
```

### Network Cards
Display gateway/network connection status.

**Layout:**
```
┌─────────────────────────────┐
│ [Icon] NETWORK NAME         │
│ Status: [Indicator]         │
│ Connected: HBLink Master    │
│ Reflector: YSF12345         │
└─────────────────────────────┘
```

**States:**
- **Connected (Cyan):** Network link active
- **Disconnected (Red):** Network offline
- **Not Configured (Gray):** Network disabled

**Example:**
```
┌─────────────────────────────┐
│ 🌐 YSF Gateway              │
│ Status: ● Connected         │  ← Cyan dot
│ Reflector: US-ALABAMA-01    │
│ Since: 2025-01-14 08:23     │
└─────────────────────────────┘
```

### System Card
Overall system health and modem status.

**Layout:**
```
┌─────────────────────────────┐
│ ⚙️  System Status           │
│ Modem: ● Connected          │  ← Green dot
│ Current Mode: DMR           │
│ Frequency: 441.000 MHz      │
│ Dashboard: 2h uptime        │
└─────────────────────────────┘
```

---

## Live Log Display

### Format
Color-coded, scrolling log view with minimal processing:

```
[12:34:56] DMR Slot 1, received RF voice from KC1XXX to TG 31665
           ^^^ Green text (DMR mode)

[12:35:12] YSF, received network voice from N0CALL to FCS012-01
           ^^^ Yellow text (YSF mode)

[12:35:45] ERROR: DMR Network connection lost
           ^^^ Red text (Error level)
```

### Structure
```html
<div class="log-line" data-mode="DMR" data-level="INFO">
  <span class="timestamp">[12:34:56]</span>
  <span class="log-text" style="color: #00ff00;">
    DMR Slot 1, received RF voice from KC1XXX to TG 31665
  </span>
</div>
```

### Features
- **Auto-scroll:** Latest messages at bottom
- **Pause on hover:** Stop scrolling when mouse over log
- **Color-coded:** Entire line colored by mode
- **Timestamp:** Always visible on left
- **Truncation:** Lines >120 chars truncated with "..."
- **Buffer limit:** 500 lines max (configurable)

---

## Layout

### Desktop View (>768px)
```
┌─────────────────────────────────────────────────┐
│ 🔷 MMDVM Dashboard          [Last Update: 1s]   │  ← Header bar
├─────────────────────────────────────────────────┤
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ │
│ │ DMR     │ │ D-Star  │ │ YSF     │ │ System │ │  ← Status cards
│ │ Active  │ │ Idle    │ │ Conn.   │ │ OK     │ │
│ └─────────┘ └─────────┘ └─────────┘ └────────┘ │
├─────────────────────────────────────────────────┤
│ Recent Activity                                  │  ← Transmission list
│ • KC1XXX → TG 31665 (DMR) 15s ago               │
│ • N0CALL → FCS012 (YSF) 1m ago                  │
│ • W1ABC → DCS001 (D-Star) 5m ago                │
├─────────────────────────────────────────────────┤
│ Live Log                              [Clear]   │  ← Live log viewer
│ [12:34:56] DMR Slot 1, received RF voice...     │
│ [12:35:12] YSF, received network voice...       │
│ [12:35:45] ERROR: DMR Network connection lost   │
│ [12:36:01] DMR, network login to HBLink         │
│ ▼ Auto-scrolling                                │
└─────────────────────────────────────────────────┘
```

### Mobile View (<768px)
Stacked layout, collapsible sections:

```
┌────────────────────────┐
│ 🔷 MMDVM Dashboard     │
├────────────────────────┤
│ Status ▼               │  ← Expandable
│ ┌──────────────────┐   │
│ │ DMR: Active      │   │
│ │ D-Star: Idle     │   │
│ │ YSF: Connected   │   │
│ └──────────────────┘   │
├────────────────────────┤
│ Activity (10) ▼        │  ← Expandable
│ • KC1XXX → TG 31665    │
│   15s ago              │
├────────────────────────┤
│ Live Log ▼             │  ← Expandable
│ [12:36:01] DMR...      │
│ [12:36:15] YSF...      │
└────────────────────────┘
```

---

## Card State Transitions

### Mode Card States

1. **Disabled → Idle**
   - Trigger: Mode enabled in config, MMDVMHost restart detected
   - Visual: Gray → Blue transition (0.3s fade)

2. **Idle → Active**
   - Trigger: Transmission detected in logs
   - Visual: Blue → Green, pulse animation (0.5s)

3. **Active → Idle**
   - Trigger: No activity for 10 seconds
   - Visual: Green → Blue fade (1s)

### Network Card States

1. **Disconnected → Connected**
   - Trigger: "network login" or "connected to" in logs
   - Visual: Red → Cyan, "connecting..." animation

2. **Connected → Disconnected**
   - Trigger: "connection lost" or timeout
   - Visual: Cyan → Red, warning icon pulse

---

## Responsive Breakpoints

| Breakpoint | Width | Layout Changes |
|------------|-------|----------------|
| **xs** | <480px | Single column, stacked cards |
| **sm** | 480-768px | Single column, larger cards |
| **md** | 768-1024px | 2-column grid, side-by-side |
| **lg** | 1024-1440px | 3-column grid, expanded log |
| **xl** | >1440px | 4-column grid, full details |

---

## Accessibility

- **Color Blind Safe:** Mode colors distinguishable in protanopia/deuteranopia
- **High Contrast:** All text meets WCAG AA standards (4.5:1 ratio)
- **Keyboard Nav:** Tab through cards, arrow keys for log scrolling
- **Screen Reader:** ARIA labels on all status indicators
- **Dark Mode Only:** Optimized for low-light viewing (shack/nighttime use)

---

## Performance Targets

### UI Update Frequency
- **Status Cards:** 1 second
- **Live Log:** 200ms (5 updates/second)
- **Transmission List:** 1 second
- **Network Status:** 5 seconds

### Animation Performance
- **Target:** 60 FPS
- **Technique:** CSS transforms (GPU accelerated)
- **Fallback:** Reduce animations on low-end devices

### Data Transfer
- **WebSocket:** <1KB per second (compressed updates)
- **Initial Load:** <50KB (HTML + CSS + JS)
- **Images:** None (icons are Unicode or SVG)

---

## Icon Set

Using Unicode characters for zero-dependency icons:

| Symbol | Unicode | Usage |
|--------|---------|-------|
| 📡 | U+1F4E1 | Radio/antenna (mode cards) |
| 🌐 | U+1F310 | Globe (network cards) |
| ⚙️ | U+2699 | Gear (system card) |
| ● | U+25CF | Status dot |
| ▶ | U+25B6 | Expand arrow |
| ▼ | U+25BC | Collapse arrow |
| ✓ | U+2713 | Success/OK |
| ✗ | U+2717 | Error/Fail |
| ⚠ | U+26A0 | Warning |

---

## Implementation Notes

### CSS Framework
**None.** Pure CSS for minimal footprint.

**Key CSS:**
```css
:root {
  --mode-dmr: #00ff00;
  --mode-dstar: #00ffff;
  --mode-ysf: #ffff00;
  --mode-p25: #ff8800;
  --mode-nxdn: #ff00ff;
  --mode-fm: #ffffff;
  --mode-system: #888888;
  
  --status-active: #00ff00;
  --status-idle: #0088ff;
  --status-connected: #00ffff;
  --status-disconnected: #ff0000;
  --status-error: #ff0000;
  
  --bg-dark: #0a0a0a;
  --bg-card: #1a1a1a;
  --text-primary: #ffffff;
  --text-secondary: #888888;
}

.log-line[data-mode="DMR"] { color: var(--mode-dmr); }
.log-line[data-mode="DSTAR"] { color: var(--mode-dstar); }
/* ... etc */

.status-indicator.active { 
  color: var(--status-active);
  animation: pulse 1.5s infinite;
}
```

### JavaScript
Vanilla JS, no frameworks. Key functions:
- `updateStatusCards(data)`
- `appendLogLine(entry)`
- `updateTransmissionList(transmissions)`
- `connectWebSocket()`

### WebSocket Message Format
```json
{
  "type": "log_update",
  "data": {
    "timestamp": "12:34:56",
    "text": "DMR Slot 1, received RF voice...",
    "mode": "DMR",
    "level": "INFO"
  }
}
```
