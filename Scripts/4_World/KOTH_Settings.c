// -----------------------------------------------------------------------------
//  KOTH_Settings - deserialised from profiles\PackFazupix\KOTH\settings.json
// -----------------------------------------------------------------------------

class KOTH_Settings
{
	//! Master switch. If false the manager never starts a round.
	bool   Enabled                  = true;

	//! "classic" | "accumulate" | "dominant"
	string CaptureMode              = "classic";

	//! Seconds a player needs to accumulate (inside zone) to finish a capture.
	int    CaptureTimeSeconds       = 120;

	//! Seconds between pre-start warnings (announced countdown).
	int    PreStartWarningEverySec  = 60;

	//! Seconds between "Starting in X" warnings in the final minute.
	int    FinalWarningEverySec     = 10;

	//! Seconds between "sendo capturado" broadcasts while a capture is in
	//! progress. 0 disables the periodic broadcast (only the initial
	//! CaptureStarted message is sent).
	int    CaptureProgressWarnEverySec = 30;

	//! Seconds between "zona contestada" broadcasts while the zone is
	//! contested. 0 disables this broadcast entirely.
	int    ContestedWarnEverySec    = 45;

	//! Seconds the pre-start countdown lasts before the zone goes ACTIVE.
	int    PreStartCountdownSec     = 300;

	//! Seconds of cooldown between rounds.
	int    CooldownSec              = 1800;

	//! Extra radius used only to count "nearby" players in the HUD counter.
	//! The capture radius itself is defined per-zone in zones.json.
	float  HudCounterExtraRadius    = 0.0;

	//! Hot reload JSON profiles every N seconds (0 disables hot reload).
	int    HotReloadIntervalSec     = 15;

	//! Maximum number of simultaneous active zones (the rest queue up).
	int    MaxConcurrentZones       = 1;

	//! If true the manager will pick zones at random, otherwise iterates the list.
	bool   RandomZoneOrder          = true;

	//! Verbosity: 0=error, 1=warn, 2=info, 3=debug
	int    LogLevel                 = 2;

	//! Whether to drop the tier loot crates on capture (if false only gives a
	//! notification to the winner - useful for debugging).
	bool   SpawnLootOnCapture       = true;

	//! Lifetime (seconds) for spawned loot crates before auto-cleanup.
	int    LootCrateLifetimeSec     = 900;

	//! Notify admin players (VPPAdminTools) on every state change.
	bool   NotifyAdmins             = true;
}
