# PackFazupix_KOTH

King of the Hill event system for **DayZ Chernarus**, designed to drop into a
full-mod server (CF, Dabs-Framework, VPPAdminTools, SNAFU-Weapons,
Paragon-Arsenal, Juggernaut-Armor, etc.).

## Features

- Pre-configured capture zones on Chernarus (NWAF, Tisy, Kamensk,
  Svetloyarsk, Balota, Krasnostav, Zelenogorsk, Vybor). Fully editable via
  `profiles\PackFazupix\KOTH\zones.json`.
- **Capture HUD**: progress bar, in-zone player counter, and current state
  ("contested", "capturando X", "inicia em Ys").
- Broadcast messages (fully customisable in `messages.json`) for:
  - Pre-start announce and periodic countdown ticks (`PreStartAnnounce`,
    `PreStartTick`).
  - Event start (`Started`).
  - When someone begins capturing (`CaptureStarted`) — everyone on the
    server sees this, with the current player count in the zone.
  - While a capture is in progress (`CaptureInProgress`) — periodic
    broadcast with leader name, player count and percent complete. Cadence
    configurable via `CaptureProgressWarnEverySec` in `settings.json`.
  - While the zone is contested (`CaptureContested`) — periodic broadcast
    with player count. Cadence via `ContestedWarnEverySec`.
  - Capture completion (`Captured`) with tier + kit information.
  - Event end (`Ended`).
- **4 loot tiers** (T1 Trash → T4 Legendary), weighted so rolls feel dynamic
  ("às vezes vem loot bom, às vezes vem loot ruim"). Each tier has N
  interchangeable kits; a kit is chosen uniformly after the tier is rolled.
  Items support `Min`/`Max` stack sizes, a `Chance`, attachments and cargo.
- Capture modes: `classic` (pauses when contested), `accumulate` (always
  earns progress), `dominant` (multi-player advantage).
- **Optimised Discord webhook** — queued + batched, async POSTs through
  `RestContext`. Never blocks the mission thread even if Discord is down.
  Rate-limit safe (flush interval configurable).
- **Hot reload**: every N seconds (configurable) the server re-reads all
  profile JSONs. Only the files whose content actually changed trigger a
  reload, so the admin can safely leave auto-reload on in production.
- Admin chat commands (route through your own admin check — see the TODO in
  `MissionServer_KOTH.c`):
  - `/kothreload` — force profile reload.
  - `/kothstart <zone_id>` — force-start a zone rotation.
  - `/kothstop  <zone_id>` — end an active rotation early.

## Installation

1. Clone/drop this repo into your mod build pipeline and pack as
   `@PackFazupix_KOTH` via **Mikero's tools** (`pboProject`) or the DayZ
   Workbench.
2. Add `@PackFazupix_KOTH` to your server launch params **after** `@CF`:
   ```
   -mod=@CF;@Dabs-Framework;@VPPAdminTools;@PackFazupix_KOTH;...
   ```
   (Client must load `@CF` + `@PackFazupix_KOTH` at minimum so the HUD
   widgets are present.)
3. Start the server once — the mod will create
   `profiles\PackFazupix\KOTH\` with five JSON files populated with working
   defaults (including the 8 pre-set Chernarus zones).
4. Edit the JSON files to taste (see examples below). Next hot-reload tick
   picks up the changes — no restart required.

## Profile files (`profiles\PackFazupix\KOTH\`)

### `settings.json`
Global event behaviour. See `Scripts/4_World/KOTH_Settings.c` for the full
list of fields. Highlights:

| Field                     | Default | Notes                                        |
|---------------------------|---------|----------------------------------------------|
| `CaptureMode`             | `"classic"` | `"classic"`, `"accumulate"`, `"dominant"` |
| `CaptureTimeSeconds`      | `120`   | Progress needed to finish a capture          |
| `PreStartCountdownSec`    | `300`   | Announce window before ACTIVE                |
| `PreStartWarningEverySec` | `60`    | Broadcast cadence during announce            |
| `FinalWarningEverySec`    | `10`    | Broadcast cadence in the last minute         |
| `CaptureProgressWarnEverySec` | `30` | "Sendo capturado" cadence (0 disables)     |
| `ContestedWarnEverySec`   | `45`    | "Zona contestada" cadence (0 disables)       |
| `CooldownSec`             | `1800`  | Between rounds                               |
| `HotReloadIntervalSec`    | `15`    | `0` disables hot-reload                      |
| `MaxConcurrentZones`      | `1`     | Increase for multi-zone servers              |
| `RandomZoneOrder`         | `true`  | Shuffle zone rotation                        |
| `SpawnLootOnCapture`      | `true`  | Disable for debugging                        |
| `LootCrateLifetimeSec`    | `900`   | Auto-cleanup for spawned loot                |

### `zones.json`
Each entry defines a capture zone. Example:

```json
{
  "Zones": [
    {
      "Id": "nwaf",
      "Name": "NW Airfield (ATC)",
      "X": 4875.0, "Y": 0.0, "Z": 9545.0,
      "Radius": 180.0,
      "CaptureTimeSeconds": 0,
      "PreStartCountdownSec": 0,
      "Schedule": [],
      "Enabled": true,
      "TierMin": 1, "TierMax": 4
    }
  ]
}
```

- Use `Y=0` to auto-resolve ground height at spawn.
- `TierMin`/`TierMax` clamp which tiers this zone can roll (useful for
  making distant zones reward better loot).

### `loot_tiers.json`
Four tiers, each with N kits. Example (abbreviated):

```json
{
  "Tiers": [
    {
      "Tier": 1, "Label": "Tier 1 - Trash", "Weight": 40,
      "Kits": [
        { "Name": "PlayerVanilla",
          "Items": [
            { "ClassName": "AKM", "Min": 1, "Max": 1, "Chance": 100 },
            { "ClassName": "Mag_AKM_30Rnd", "Min": 2, "Max": 3, "Chance": 100 }
          ]
        }
      ]
    }
  ]
}
```

- `Weight` is the relative probability of that tier being rolled.
  Defaults: T1=40, T2=30, T3=20, T4=10 (70% chance of a T1/T2 outcome).
- Replace the placeholder classnames with real ones from your mod list
  (`@SNAFU-Weapons`, `@Paragon-Arsenal`, `@Juggernaut-Armor`,
  `@Altyn-helmet`, `@Matrix-Clothing-Set`, `@BallerZ-Gear`, etc.). Invalid
  classnames are logged with `[KOTH][WARN] Loot classname not found: ...`
  so you can spot typos quickly.

### `messages.json`
Every broadcast string is templated. Supported placeholders:
`{zone}`, `{seconds}`, `{minutes}`, `{player}`, `{tier}`, `{count}`,
`{percent}` (only in `CaptureInProgress`).

### `webhook.json`
Discord webhook. **Never commit this file.** Relevant fields:

| Field              | Purpose                                               |
|--------------------|-------------------------------------------------------|
| `Enabled`          | Master switch                                         |
| `Url`              | Full Discord webhook URL                              |
| `BatchSize`        | Embeds per POST (Discord caps at 10)                  |
| `FlushIntervalSec` | How often the queue is flushed                        |
| `MaxQueueSize`     | Queue cap — oldest embeds dropped past this           |
| `MaxRetries`       | Retries per batch on 5xx/timeout (default `5`)        |
| `MaxBackoffSec`    | Cap for exponential backoff between retries (`60`)    |
| `Send*`            | Toggle each event type independently                  |

The webhook is **hardened against downtime and rate-limits**:
- In-flight guard: only one POST in flight at a time (slow Discord never
  causes overlapping requests to pile up).
- Retry budget: failed batches are re-queued (at the front, preserving FIFO)
  up to `MaxRetries` times, with exponential backoff (`2^attempt` seconds,
  clamped at `MaxBackoffSec`). Healthy POSTs reset the backoff.
- Permanent-failure codes (`400`/`401`/`403`/`404`) are never retried — the
  batch is dropped immediately and logged.
- Payload cap: embed descriptions are truncated at 3500 chars so a runaway
  string can't blow past Discord's 6000-char per-embed cap.
- Metric log line every 10 flushes:
  `[KOTH][INFO][webhook] metrics queued=X sent=Y dropped=Z retries=R flushes=F`.

## Dependencies

- **CommunityFramework** (`@CF`) — required. Used for the RPC pipeline and
  future permission-gated admin commands.
- Optional but recommended (not required for the mod to load):
  - `@Dabs-Framework` — nicer in-game notifications if present; the mod
    falls back to its own toast if not.
  - `@VPPAdminTools` — hook your own admin check into
    `MissionServer_KOTH.IsAdmin()` to gate `/koth*` chat commands.

## Capture mode details

- **classic** (default): any non-allied presence inside the zone pauses the
  leader's capture progress (broadcast: `CaptureContested`). This matches
  the traditional KOTH feel.
- **accumulate**: every player inside the zone always gains progress. Use
  for casual / PvE servers.
- **dominant**: every player gains progress at a rate that scales with how
  many allies they have inside the zone (sqrt scaling so 5 allies isn't 5×).

## Smoke-test checklist (recommended before production)

The mod was code-reviewed but **not executed against a live DayZ server**
during development (Devin does not run DayZ server binaries). Before
shipping:

1. Pack and load on a local test server.
2. Verify `profiles\PackFazupix\KOTH\` is created with all five JSON files.
3. Wait for the first `ANNOUNCED` broadcast — confirm the countdown ticks
   in global chat.
4. Enter the zone solo — confirm the HUD appears, the progress bar fills,
   and the player counter reads `1`.
5. Have a second player enter — confirm (in `classic` mode) the bar pauses
   and the HUD shows `CONTESTADO`, and that the counter updates to `2`.
6. Let one player finish a capture — confirm the `Captured` broadcast, the
   Discord embed, and the loot crate spawn.
7. Edit `loot_tiers.json` in place, wait ≤ `HotReloadIntervalSec` and
   confirm `[KOTH][INFO] loot_tiers.json (re)loaded` appears in the log.

## File layout

```
PackFazupix_KOTH/
├── mod.cpp
├── config.cpp
├── Scripts/
│   ├── 3_Game/       # shared constants + logger
│   ├── 4_World/      # Manager, Zone, Profile, Webhook, LootSpawner, RPC
│   └── 5_Mission/    # MissionServer, MissionGameplay, HUD
├── GUI/layouts/KOTH/ # capture_hud.layout
└── README.md
```
