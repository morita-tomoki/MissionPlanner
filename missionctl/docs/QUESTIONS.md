# Questions — decisions needing the human

When a choice is ambiguous, irreversible, or changes the architecture, park it here
and move on to a different slice. The human answers asynchronously. When answered,
move the item to an ADR (if it's a real decision) or DISCOVERIES, and delete it here.

Format:
```
## Q<n> — <short title>   [status: OPEN | ANSWERED]
Context: ...
Options: A) ...  B) ...
Recommendation: ...
Answer: (human fills in)
```

---

## Q1 — Map provider for the QML view   [status: OPEN]
Context: M5 needs a moving-map. Legacy used GMap.NET (Windows).
Options: A) QtLocation + OSM plugin (offline tiles possible)  B) embed a web map.
Recommendation: A (native QtQuick, offline-capable, no browser dependency).
Answer:

## Q3 — Flight-mode name mapping   [status: OPEN]
Context: HEARTBEAT gives a numeric `custom_mode`; the human-readable name
(e.g. GUIDED, LOITER, AUTO) depends on vehicle type (Copter/Plane/Rover differ).
State currently stores the raw number only.
Options: A) map to names in the presentation layer using a per-MAV_TYPE table
         (pymavlink's `mode_mapping_*` helpers). B) resolve in core once MAV_TYPE
         is known from HEARTBEAT.
Recommendation: A — keep core numeric/SI; names are a display concern.
Answer:

## Q2 — Headless daemon now or later?   [status: OPEN]
Context: A separate core process (ZeroMQ/WebSocket) isolates links from UI crashes
and enables multi-operator, but adds IPC complexity for a solo dev.
Options: A) single process now, keep FleetManager API clean for later split.
         B) daemon from the start.
Recommendation: A (defer; the clean API boundary makes the later split bounded).
Answer:
