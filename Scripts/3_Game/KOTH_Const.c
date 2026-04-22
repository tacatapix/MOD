// -----------------------------------------------------------------------------
//  PackFazupix_KOTH - shared constants (3_Game)
// -----------------------------------------------------------------------------
//  Values here are available to both server and client scripts, and to the
//  JSON profile loader. Do not put gameplay logic here - only constants and
//  version strings.
// -----------------------------------------------------------------------------

class KOTH_Const
{
	static const string MOD_NAME        = "PackFazupix_KOTH";
	static const string MOD_VERSION     = "1.0.0";

	// Absolute profile folder (relative to the DayZ server profiles directory,
	// which DayZ exposes as "$profile:").
	static const string PROFILE_DIR     = "$profile:PackFazupix\\KOTH\\";

	// JSON files under PROFILE_DIR
	static const string FILE_SETTINGS   = "settings.json";
	static const string FILE_ZONES      = "zones.json";
	static const string FILE_LOOT       = "loot_tiers.json";
	static const string FILE_MESSAGES   = "messages.json";
	static const string FILE_WEBHOOK    = "webhook.json";

	// Capture modes (string values stored in settings.json)
	static const string MODE_CLASSIC    = "classic";    // pauses when contested
	static const string MODE_ACCUMULATE = "accumulate"; // always progresses when inside
	static const string MODE_DOMINANT   = "dominant";   // faster with more allies

	// Zone lifecycle states
	static const int STATE_IDLE         = 0;
	static const int STATE_ANNOUNCED    = 1;  // pre-start countdown running
	static const int STATE_ACTIVE       = 2;  // capture in progress
	static const int STATE_CAPTURED     = 3;  // someone finished capture
	static const int STATE_COOLDOWN     = 4;  // cooling down before next cycle

	// Default tick rate for the server KOTH loop (ms)
	static const int SERVER_TICK_MS     = 1000;

	// Default reload tick for JSON hot-reload (ms)
	static const int RELOAD_TICK_MS     = 5000;
}
