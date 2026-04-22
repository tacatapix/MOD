// -----------------------------------------------------------------------------
//  KOTH_Zone - a single capture zone, loaded from zones.json
// -----------------------------------------------------------------------------

class KOTH_Zone
{
	//! Unique id - used in logs, webhook payloads and RPC sync.
	string Id                 = "";

	//! Friendly display name shown on HUD and broadcast messages.
	string Name               = "";

	//! World coordinates (Chernarus). X and Z are horizontal; Y is height.
	//! If Y is 0 the zone will resolve ground height at runtime.
	float  X                  = 0.0;
	float  Y                  = 0.0;
	float  Z                  = 0.0;

	//! Capture radius in metres.
	float  Radius             = 150.0;

	//! Per-zone override for capture time (0 uses the global setting).
	int    CaptureTimeSeconds = 0;

	//! Per-zone override for pre-start countdown (0 uses the global setting).
	int    PreStartCountdownSec = 0;

	//! Schedule - if empty the zone is pickable at any time.
	//! Entries are 24h strings like "18:00", "22:30".
	ref array<string> Schedule;

	//! If true the zone is currently enabled for rotation.
	bool   Enabled            = true;

	//! Restriction - only allow this zone to roll T1..T4 (inclusive).
	//! Use 0,0 to allow the full range.
	int    TierMin            = 1;
	int    TierMax            = 4;

	vector GetPosition()
	{
		vector pos = Vector(X, Y, Z);
		if (Y == 0.0)
		{
#ifdef SERVER
			pos[1] = GetGame().SurfaceY(X, Z);
#endif
		}
		return pos;
	}
}

class KOTH_ZonesFile
{
	ref array<ref KOTH_Zone> Zones;
}
