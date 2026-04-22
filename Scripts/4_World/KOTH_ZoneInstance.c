// -----------------------------------------------------------------------------
//  KOTH_ZoneInstance - runtime state for a single zone currently in rotation.
//
//  Owned by KOTH_Manager on the server. Never serialised: rebuilt from
//  zones.json on hot-reload.
// -----------------------------------------------------------------------------

class KOTH_ZoneProgress
{
	string PlayerId;
	string PlayerName;
	float  Accumulated;   // 0..CaptureTimeSeconds
}

class KOTH_ZoneInstance
{
	ref KOTH_Zone                          Def;

	int                                    State           = KOTH_Const.STATE_IDLE;
	int                                    StateTimerMs    = 0;     // ms remaining in current state

	ref array<string>                      PlayersInZone;          // DayZ player UIDs currently inside
	ref map<string, ref KOTH_ZoneProgress> ProgressByPlayer;
	int                                    LastWarnTickMs         = 0; // pre-start warnings
	int                                    LastProgressWarnTickMs = 0; // "sendo capturado" broadcast
	int                                    LastContestedWarnTickMs= 0; // "zona contestada" broadcast

	string                                 LeadingPlayerId;
	string                                 LeadingPlayerName;
	float                                  LeadingProgress;
	bool                                   Contested;

	void KOTH_ZoneInstance(KOTH_Zone def)
	{
		Def                = def;
		PlayersInZone      = new array<string>();
		ProgressByPlayer   = new map<string, ref KOTH_ZoneProgress>();
	}

	float ProgressPct(int captureTimeSec)
	{
		if (captureTimeSec <= 0) return 0;
		return LeadingProgress / captureTimeSec;
	}

	void Reset()
	{
		PlayersInZone.Clear();
		ProgressByPlayer.Clear();
		LeadingPlayerId   = "";
		LeadingPlayerName = "";
		LeadingProgress   = 0;
		Contested         = false;
	}
}
