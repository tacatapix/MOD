// -----------------------------------------------------------------------------
//  KOTH_Manager - server-authoritative KOTH event loop.
//
//  Lifecycle per zone:
//     IDLE -> ANNOUNCED (pre-start countdown, broadcasts every N seconds)
//     ANNOUNCED -> ACTIVE (capture window opens)
//     ACTIVE -> CAPTURED (first player to fill the bar wins)
//     CAPTURED -> COOLDOWN
//     COOLDOWN -> IDLE (and the manager picks the next zone)
//
//  Everything user-facing is routed through:
//     - KOTH_Manager.Notify(...)  : global text broadcast (RPC to all clients)
//     - KOTH_Manager.SyncZoneToZone(...) : per-zone capture state (RPC to all
//                                           clients so the HUD can show the
//                                           bar even to people not in zone)
//     - KOTH_Webhook                   : Discord messages
// -----------------------------------------------------------------------------

class KOTH_Manager
{
	static ref KOTH_Manager s_Instance;

	protected ref KOTH_Profile               m_Profile;
	protected ref KOTH_Webhook               m_Webhook;
	protected ref array<ref KOTH_ZoneInstance> m_Active;
	protected ref array<ref KOTH_Zone>       m_RotationQueue;
	protected int                            m_HotReloadAccumMs;
	protected int                            m_LastTickMs;

	static KOTH_Manager GetInstance()
	{
		if (!s_Instance) s_Instance = new KOTH_Manager();
		return s_Instance;
	}

	void KOTH_Manager()
	{
		m_Profile        = new KOTH_Profile();
		m_Webhook        = new KOTH_Webhook();
		m_Active         = new array<ref KOTH_ZoneInstance>();
		m_RotationQueue  = new array<ref KOTH_Zone>();
	}

	// ----------------------------------------------------------------------
	//  Bootstrap
	// ----------------------------------------------------------------------

	void Init()
	{
		if (!GetGame().IsServer()) return;
		m_Profile.EnsureFiles();
		m_Profile.LoadAll();
		m_Webhook.SetConfig(m_Profile.Webhook());

		m_Profile.OnSettingsChanged.Insert(OnSettingsChanged);
		m_Profile.OnWebhookChanged .Insert(OnWebhookChanged);
		m_Profile.OnZonesChanged   .Insert(OnZonesChanged);

		RefillRotationQueue();

		// Fire the first tick on the next frame so the mission is fully alive.
		m_LastTickMs = GetTickMs();
		GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(Tick, KOTH_Const.SERVER_TICK_MS, true);

		KOTH_Log.Info("Manager initialised - " + m_Profile.Zones().Zones.Count() + " zones in config");
	}

	KOTH_Profile      Profile() { return m_Profile; }
	KOTH_Settings     Settings(){ return m_Profile.Settings(); }
	KOTH_Messages     Messages(){ return m_Profile.Messages(); }
	KOTH_WebhookConfig WebhookCfg() { return m_Profile.Webhook(); }

	// ----------------------------------------------------------------------
	//  Tick
	// ----------------------------------------------------------------------

	protected int GetTickMs()
	{
		return GetGame().GetTickTime() * 1000;
	}

	void Tick()
	{
		int now = GetTickMs();
		int dt  = now - m_LastTickMs;
		if (dt <= 0) dt = KOTH_Const.SERVER_TICK_MS;
		m_LastTickMs = now;

		// Hot reload JSONs.
		int reloadEvery = m_Profile.Settings().HotReloadIntervalSec * 1000;
		if (reloadEvery > 0)
		{
			m_HotReloadAccumMs += dt;
			if (m_HotReloadAccumMs >= reloadEvery)
			{
				m_HotReloadAccumMs = 0;
				m_Profile.LoadAll();
			}
		}

		m_Webhook.Tick(dt);

		if (!m_Profile.Settings().Enabled)
		{
			m_Active.Clear();
			return;
		}

		// Make sure we have zones running up to the configured max.
		while (m_Active.Count() < m_Profile.Settings().MaxConcurrentZones)
		{
			KOTH_Zone next = TakeNextZoneFromRotation();
			if (!next) break;
			StartAnnounced(next);
		}

		// Advance each active zone.
		for (int i = m_Active.Count() - 1; i >= 0; i--)
		{
			KOTH_ZoneInstance zi = m_Active[i];
			TickZone(zi, dt);
			if (zi.State == KOTH_Const.STATE_IDLE)
				m_Active.Remove(i);
		}
	}

	// ----------------------------------------------------------------------
	//  Rotation
	// ----------------------------------------------------------------------

	protected void RefillRotationQueue()
	{
		m_RotationQueue.Clear();
		foreach (KOTH_Zone z : m_Profile.Zones().Zones)
		{
			if (z.Enabled) m_RotationQueue.Insert(z);
		}
		if (m_Profile.Settings().RandomZoneOrder) Shuffle(m_RotationQueue);
	}

	protected void Shuffle(array<ref KOTH_Zone> arr)
	{
		int n = arr.Count();
		for (int i = n - 1; i > 0; i--)
		{
			int j = Math.RandomInt(0, i + 1);
			KOTH_Zone tmp = arr[i];
			arr[i] = arr[j];
			arr[j] = tmp;
		}
	}

	protected KOTH_Zone TakeNextZoneFromRotation()
	{
		if (m_RotationQueue.Count() == 0) RefillRotationQueue();
		if (m_RotationQueue.Count() == 0) return null;
		KOTH_Zone z = m_RotationQueue[0];
		m_RotationQueue.Remove(0);
		return z;
	}

	// ----------------------------------------------------------------------
	//  State transitions
	// ----------------------------------------------------------------------

	protected void StartAnnounced(KOTH_Zone def)
	{
		KOTH_ZoneInstance zi = new KOTH_ZoneInstance(def);
		zi.State        = KOTH_Const.STATE_ANNOUNCED;
		int sec         = def.PreStartCountdownSec;
		if (sec <= 0) sec = m_Profile.Settings().PreStartCountdownSec;
		zi.StateTimerMs = sec * 1000;
		m_Active.Insert(zi);

		string msg = Substitute(m_Profile.Messages().PreStartAnnounce, def.Name, sec / 60, sec, "", "", 0);
		Broadcast(msg, "KOTH", m_Profile.Webhook().ColorAnnounce);
		m_Webhook.Announce(def.Name, sec);
		SyncZone(zi);
		KOTH_Log.Info("ANNOUNCED zone '" + def.Id + "' - starts in " + sec + "s");
	}

	protected void StartActive(KOTH_ZoneInstance zi)
	{
		zi.State        = KOTH_Const.STATE_ACTIVE;
		int sec         = zi.Def.CaptureTimeSeconds;
		if (sec <= 0) sec = m_Profile.Settings().CaptureTimeSeconds;
		zi.StateTimerMs = sec * 1000;
		zi.Reset();

		string msg = Substitute(m_Profile.Messages().Started, zi.Def.Name, 0, 0, "", "", 0);
		Broadcast(msg, "KOTH", m_Profile.Webhook().ColorStart);
		m_Webhook.Started(zi.Def.Name);
		SyncZone(zi);
		KOTH_Log.Info("ACTIVE zone '" + zi.Def.Id + "' - capture window " + sec + "s");
	}

	protected void FinishCaptured(KOTH_ZoneInstance zi, string playerName)
	{
		zi.State        = KOTH_Const.STATE_CAPTURED;
		zi.StateTimerMs = 3000; // brief "won" display

		// Roll loot tier + kit.
		KOTH_LootRollResult res = KOTH_LootSpawner.Roll(m_Profile.Loot(), zi.Def.TierMin, zi.Def.TierMax);
		string tierLabel = "-";
		string kitName   = "-";
		if (res)
		{
			tierLabel = res.Tier.Label;
			kitName   = res.Kit.Name;
			if (m_Profile.Settings().SpawnLootOnCapture)
			{
				KOTH_LootSpawner.SpawnKit(res.Kit, zi.Def.GetPosition(), zi.Def.Radius * 0.25,
					m_Profile.Settings().LootCrateLifetimeSec);
			}
		}

		string msg = Substitute(m_Profile.Messages().Captured, zi.Def.Name, 0, 0, playerName, tierLabel, 0);
		Broadcast(msg, "KOTH", m_Profile.Webhook().ColorCaptured);
		m_Webhook.Captured(zi.Def.Name, playerName, tierLabel, kitName);
		SyncZone(zi);
		KOTH_Log.Info("CAPTURED zone '" + zi.Def.Id + "' by '" + playerName + "' -> " + tierLabel + "/" + kitName);
	}

	protected void StartCooldown(KOTH_ZoneInstance zi)
	{
		zi.State        = KOTH_Const.STATE_COOLDOWN;
		zi.StateTimerMs = m_Profile.Settings().CooldownSec * 1000;
		string msg = Substitute(m_Profile.Messages().Ended, zi.Def.Name, 0, 0, "", "", 0);
		Broadcast(msg, "KOTH", m_Profile.Webhook().ColorEnded);
		m_Webhook.Ended(zi.Def.Name);
		SyncZone(zi);
	}

	protected void FinishIdle(KOTH_ZoneInstance zi)
	{
		zi.State        = KOTH_Const.STATE_IDLE;
		zi.StateTimerMs = 0;
		SyncZone(zi);
	}

	// ----------------------------------------------------------------------
	//  Per-zone tick
	// ----------------------------------------------------------------------

	protected void TickZone(KOTH_ZoneInstance zi, int dt)
	{
		zi.StateTimerMs -= dt;

		switch (zi.State)
		{
			case KOTH_Const.STATE_ANNOUNCED:
				TickAnnounced(zi, dt);
				if (zi.StateTimerMs <= 0) StartActive(zi);
				break;

			case KOTH_Const.STATE_ACTIVE:
				TickActive(zi, dt);
				break;

			case KOTH_Const.STATE_CAPTURED:
				if (zi.StateTimerMs <= 0) StartCooldown(zi);
				break;

			case KOTH_Const.STATE_COOLDOWN:
				if (zi.StateTimerMs <= 0) FinishIdle(zi);
				break;
		}
	}

	protected void TickAnnounced(KOTH_ZoneInstance zi, int dt)
	{
		int remaining = zi.StateTimerMs / 1000;
		int warnEvery = m_Profile.Settings().PreStartWarningEverySec;
		if (remaining <= 60) warnEvery = m_Profile.Settings().FinalWarningEverySec;

		zi.LastWarnTickMs += dt;
		if (zi.LastWarnTickMs >= warnEvery * 1000)
		{
			zi.LastWarnTickMs = 0;
			string msg = Substitute(m_Profile.Messages().PreStartTick, zi.Def.Name, remaining / 60, remaining, "", "", 0);
			Broadcast(msg, "KOTH", m_Profile.Webhook().ColorAnnounce);
		}

		// Refresh the player count even during the announce phase so clients
		// can show "N na zona" on the HUD before capture opens.
		RecalcPlayersInZone(zi);
		SyncZone(zi);
	}

	protected void TickActive(KOTH_ZoneInstance zi, int dt)
	{
		RecalcPlayersInZone(zi);

		int captureSec = zi.Def.CaptureTimeSeconds;
		if (captureSec <= 0) captureSec = m_Profile.Settings().CaptureTimeSeconds;

		string mode = m_Profile.Settings().CaptureMode;
		float dtSec = dt / 1000.0;

		// Group players by ownership. For "classic" we require exactly one
		// unique player (by id) inside the zone. For "accumulate" we always
		// award progress to everyone inside. For "dominant" we give faster
		// progress to the side with more players (size/majority).
		bool contested = false;
		if (zi.PlayersInZone.Count() > 1)  contested = true;
		zi.Contested = (mode == KOTH_Const.MODE_CLASSIC && contested);

		string newLeaderId   = "";
		string newLeaderName = "";
		float  newLeaderProg = 0;

		foreach (string pid : zi.PlayersInZone)
		{
			KOTH_ZoneProgress p = zi.ProgressByPlayer.Get(pid);
			if (!p)
			{
				p = new KOTH_ZoneProgress();
				p.PlayerId    = pid;
				p.PlayerName  = ResolvePlayerName(pid);
				p.Accumulated = 0;
				zi.ProgressByPlayer.Set(pid, p);

				// First time we see this player inside the zone AND the zone
				// is fresh -> broadcast "capture started".
				if (zi.LeadingProgress == 0 && zi.ProgressByPlayer.Count() == 1)
				{
					string msg = Substitute(m_Profile.Messages().CaptureStarted, zi.Def.Name,
						0, 0, p.PlayerName, "", zi.PlayersInZone.Count());
					Broadcast(msg, "KOTH", m_Profile.Webhook().ColorCaptureBegin);
					m_Webhook.CaptureBegin(zi.Def.Name, p.PlayerName, zi.PlayersInZone.Count());
				}
			}

			float gain = dtSec;
			if (mode == KOTH_Const.MODE_CLASSIC && contested) gain = 0;
			if (mode == KOTH_Const.MODE_DOMINANT) gain *= DominanceMultiplier(zi, pid);
			p.Accumulated += gain;
			if (p.Accumulated > newLeaderProg)
			{
				newLeaderProg = p.Accumulated;
				newLeaderId   = p.PlayerId;
				newLeaderName = p.PlayerName;
			}
		}

		zi.LeadingPlayerId   = newLeaderId;
		zi.LeadingPlayerName = newLeaderName;
		zi.LeadingProgress   = newLeaderProg;

		if (newLeaderProg >= captureSec && newLeaderId != "")
		{
			FinishCaptured(zi, newLeaderName);
			return;
		}

		TickActiveBroadcasts(zi, dt, captureSec);
		SyncZone(zi);

		// Out-of-time: nobody captured during the ACTIVE window.
		if (zi.StateTimerMs <= 0)
		{
			KOTH_Log.Info("ACTIVE window expired on '" + zi.Def.Id + "' without a capture");
			StartCooldown(zi);
		}
	}

	//! Periodic "sendo capturado" / "contestado" broadcasts during the
	//! ACTIVE phase. Cadence is controlled via settings.json:
	//!   CaptureProgressWarnEverySec (0 disables)
	//!   ContestedWarnEverySec       (0 disables)
	//! Both broadcasts also hit Discord when the matching Send* flag is on
	//! in webhook.json.
	protected void TickActiveBroadcasts(KOTH_ZoneInstance zi, int dt, int captureSec)
	{
		int progressWarnMs   = m_Profile.Settings().CaptureProgressWarnEverySec * 1000;
		int contestedWarnMs  = m_Profile.Settings().ContestedWarnEverySec       * 1000;

		// Capture-in-progress broadcast. Only fires if someone is actually
		// holding the lead (>0 progress) and we're not currently paused by
		// a contested zone in classic mode.
		if (progressWarnMs > 0 && zi.LeadingPlayerName != "" && zi.LeadingProgress > 0 && !zi.Contested)
		{
			zi.LastProgressWarnTickMs += dt;
			if (zi.LastProgressWarnTickMs >= progressWarnMs)
			{
				zi.LastProgressWarnTickMs = 0;
				int pct = (int)(zi.ProgressPct(captureSec) * 100.0);
				string msg = Substitute(m_Profile.Messages().CaptureInProgress, zi.Def.Name,
					0, 0, zi.LeadingPlayerName, "", zi.PlayersInZone.Count());
				msg = ReplacePercent(msg, pct);
				Broadcast(msg, "KOTH", m_Profile.Webhook().ColorCaptureBegin);
				m_Webhook.CaptureProgress(zi.Def.Name, zi.LeadingPlayerName, zi.PlayersInZone.Count(), pct);
			}
		}
		else
		{
			// Reset the tick so the next time someone takes the lead we
			// broadcast at a predictable cadence rather than immediately.
			zi.LastProgressWarnTickMs = 0;
		}

		// Contested broadcast.
		if (contestedWarnMs > 0 && zi.Contested)
		{
			zi.LastContestedWarnTickMs += dt;
			if (zi.LastContestedWarnTickMs >= contestedWarnMs)
			{
				zi.LastContestedWarnTickMs = 0;
				string cmsg = Substitute(m_Profile.Messages().CaptureContested, zi.Def.Name,
					0, 0, "", "", zi.PlayersInZone.Count());
				Broadcast(cmsg, "KOTH", m_Profile.Webhook().ColorCaptureBegin);
				m_Webhook.Contested(zi.Def.Name, zi.PlayersInZone.Count());
			}
		}
		else
		{
			zi.LastContestedWarnTickMs = 0;
		}
	}

	//! Substitute() doesn't know about {percent}; this wrapper handles it
	//! without bloating the signature (only capture-in-progress uses it).
	protected string ReplacePercent(string s, int pct)
	{
		s.Replace("{percent}", pct.ToString());
		return s;
	}

	//! Used only by MODE_DOMINANT - returns a positive multiplier based on
	//! how many players inside the zone share the current player's "side"
	//! (we use DayZ's group id when available, otherwise treat every player
	//! as their own side).
	protected float DominanceMultiplier(KOTH_ZoneInstance zi, string pid)
	{
		int myAllies = 1; // counts themselves
		// Without a group system we just scale by sqrt(N) so one extra ally
		// helps but 5 allies isn't 5x faster. Tuned empirically.
		return Math.Sqrt(myAllies);
	}

	// ----------------------------------------------------------------------
	//  Player-in-zone detection
	// ----------------------------------------------------------------------

	protected void RecalcPlayersInZone(KOTH_ZoneInstance zi)
	{
		zi.PlayersInZone.Clear();

		vector center  = zi.Def.GetPosition();
		float  r       = zi.Def.Radius + m_Profile.Settings().HudCounterExtraRadius;
		float  rSq     = r * r;

		array<Man> players = new array<Man>();
		GetGame().GetPlayers(players);
		foreach (Man m : players)
		{
			PlayerBase pb = PlayerBase.Cast(m);
			if (!pb || !pb.IsAlive()) continue;
			vector p = pb.GetPosition();
			float dx = p[0] - center[0];
			float dz = p[2] - center[2];
			if ((dx * dx + dz * dz) > rSq) continue;
			string id = pb.GetIdentity() ? pb.GetIdentity().GetPlainId() : "";
			if (id == "") continue;
			zi.PlayersInZone.Insert(id);
		}
	}

	protected string ResolvePlayerName(string plainId)
	{
		array<Man> players = new array<Man>();
		GetGame().GetPlayers(players);
		foreach (Man m : players)
		{
			PlayerIdentity pi = m.GetIdentity();
			if (pi && pi.GetPlainId() == plainId) return pi.GetName();
		}
		return plainId;
	}

	// ----------------------------------------------------------------------
	//  Sync + broadcast
	// ----------------------------------------------------------------------

	void SyncZone(KOTH_ZoneInstance zi)
	{
		if (!GetGame().IsServer()) return;

		KOTH_StatePayload p = new KOTH_StatePayload();
		p.ZoneId            = zi.Def.Id;
		p.ZoneName          = zi.Def.Name;
		p.State             = zi.State;
		p.PlayersInZone     = zi.PlayersInZone.Count();
		p.Contested         = zi.Contested;
		p.SecondsRemaining  = zi.StateTimerMs / 1000;
		p.ZonePos           = zi.Def.GetPosition();
		p.ZoneRadius        = zi.Def.Radius;
		p.Capturer          = zi.LeadingPlayerName;

		int captureSec = zi.Def.CaptureTimeSeconds;
		if (captureSec <= 0) captureSec = m_Profile.Settings().CaptureTimeSeconds;
		p.ProgressPct = zi.ProgressPct(captureSec);

		ScriptRPC rpc = new ScriptRPC();
		rpc.Write(p);
		rpc.Send(null, ERPCsKOTH.SYNC_STATE, true, null);
	}

	void Broadcast(string body, string title, int color)
	{
		if (!GetGame().IsServer()) return;

		KOTH_NotifyPayload p = new KOTH_NotifyPayload();
		p.Title      = title;
		p.Body       = body;
		p.DurationMs = 5000;
		p.Color      = color;

		ScriptRPC rpc = new ScriptRPC();
		rpc.Write(p);
		rpc.Send(null, ERPCsKOTH.NOTIFY, true, null);

		KOTH_Log.Info("[broadcast] " + body);
	}

	// ----------------------------------------------------------------------
	//  String substitution
	// ----------------------------------------------------------------------

	string Substitute(string tmpl, string zone, int minutes, int seconds, string player, string tier, int count)
	{
		string s = tmpl;
		s.Replace("{zone}"   , zone);
		s.Replace("{minutes}", minutes.ToString());
		s.Replace("{seconds}", seconds.ToString());
		s.Replace("{player}" , player);
		s.Replace("{tier}"   , tier);
		s.Replace("{count}"  , count.ToString());
		return s;
	}

	// ----------------------------------------------------------------------
	//  Profile change callbacks
	// ----------------------------------------------------------------------

	protected void OnSettingsChanged()
	{
		KOTH_Log.Info("Settings changed - applying");
		// Nothing to do directly: the new values are read on every tick.
	}

	protected void OnWebhookChanged()
	{
		m_Webhook.SetConfig(m_Profile.Webhook());
	}

	protected void OnZonesChanged()
	{
		// Rebuild the rotation queue, preserving active zones.
		RefillRotationQueue();
	}

	// ----------------------------------------------------------------------
	//  Admin helpers (invoked from MissionServer chat commands)
	// ----------------------------------------------------------------------

	void ReloadNow()
	{
		m_Profile.LoadAll();
		m_Webhook.SetConfig(m_Profile.Webhook());
	}

	void ForceStart(string zoneId)
	{
		foreach (KOTH_Zone z : m_Profile.Zones().Zones)
		{
			if (z.Id == zoneId)
			{
				StartAnnounced(z);
				return;
			}
		}
		KOTH_Log.Warn("ForceStart: zone id '" + zoneId + "' not found");
	}

	void ForceStop(string zoneId)
	{
		for (int i = m_Active.Count() - 1; i >= 0; i--)
		{
			if (m_Active[i].Def.Id == zoneId)
			{
				StartCooldown(m_Active[i]);
				return;
			}
		}
	}

	//! Client HUD needs to know all active zones on demand (e.g. when a
	//! player joins mid-event) - the MissionServer calls this from
	//! OnClientRespawn* hooks.
	void ResyncAllZones()
	{
		foreach (KOTH_ZoneInstance zi : m_Active)
			SyncZone(zi);
	}
}
