// -----------------------------------------------------------------------------
//  KOTH_RPC - RPC identifiers shared between server and client.
//
//  We route these through CF (CommunityFramework) when present, falling back
//  to the vanilla ScriptRPC namespace. Keep the IDs within the mod-local
//  range so they never collide with other mods.
// -----------------------------------------------------------------------------

enum ERPCsKOTH
{
	// Server -> client
	SYNC_STATE       = 25001, //!< zone state + capture progress + count
	NOTIFY           = 25002, //!< broadcast toast message

	// Client -> server (reserved for future use, e.g. admin panel)
	ADMIN_RELOAD     = 25101
}

//! Payload for SYNC_STATE (kept small - sent every tick to clients inside or
//! near an active zone).
class KOTH_StatePayload
{
	string ZoneId;
	string ZoneName;
	int    State;           // KOTH_Const.STATE_*
	float  ProgressPct;     // 0..1
	int    PlayersInZone;
	bool   Contested;
	int    SecondsRemaining;// seconds until next state transition
	vector ZonePos;
	float  ZoneRadius;
	string Capturer;        // player name currently leading capture (may be "")
}

//! Payload for NOTIFY (toast popup).
class KOTH_NotifyPayload
{
	string Title;
	string Body;
	int    DurationMs;
	int    Color;           // decimal RGB
}
