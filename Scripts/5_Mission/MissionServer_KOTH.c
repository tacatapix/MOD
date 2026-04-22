// -----------------------------------------------------------------------------
//  MissionServer_KOTH - hooks the KOTH_Manager into the DayZ server mission.
//
//  We extend MissionServer via the standard Enforce script "modded" keyword.
//  On mission start we boot the manager; on client connect we resync state
//  so the HUD on the joining player is immediately populated.
// -----------------------------------------------------------------------------

modded class MissionServer
{
	override void OnInit()
	{
		super.OnInit();
		KOTH_Manager.GetInstance().Init();
	}

	override void OnClientReadyEvent(PlayerIdentity identity, PlayerBase player)
	{
		super.OnClientReadyEvent(identity, player);
		KOTH_Manager.GetInstance().ResyncAllZones();
	}

	override void OnClientRespawnEvent(PlayerIdentity identity, PlayerBase player)
	{
		super.OnClientRespawnEvent(identity, player);
		KOTH_Manager.GetInstance().ResyncAllZones();
	}

	// Admin chat commands. We piggy-back on the built-in mission tick so we
	// don't need a separate input hook.
	void KOTH_HandleAdminChat(PlayerBase sender, string text)
	{
		if (!sender || !sender.GetIdentity()) return;
		if (!IsAdmin(sender.GetIdentity()))   return;

		string cmd = text;
		cmd.ToLower();
		if (cmd == "/kothreload")
		{
			KOTH_Manager.GetInstance().ReloadNow();
			SendAdmin(sender, "[KOTH] profiles reloaded.");
			return;
		}
		if (cmd.IndexOf("/kothstart ") == 0)
		{
			string zoneId = text.Substring(11, text.Length() - 11);
			KOTH_Manager.GetInstance().ForceStart(zoneId);
			SendAdmin(sender, "[KOTH] force-started '" + zoneId + "'.");
			return;
		}
		if (cmd.IndexOf("/kothstop ") == 0)
		{
			string zoneId2 = text.Substring(10, text.Length() - 10);
			KOTH_Manager.GetInstance().ForceStop(zoneId2);
			SendAdmin(sender, "[KOTH] stopped '" + zoneId2 + "'.");
			return;
		}
	}

	protected bool IsAdmin(PlayerIdentity id)
	{
		// Replace with your own logic (e.g. VPPAdminTools permissions, CF
		// permissions or a hardcoded SteamID allowlist).
		return false;
	}

	protected void SendAdmin(PlayerBase to, string msg)
	{
		KOTH_NotifyPayload p = new KOTH_NotifyPayload();
		p.Title      = "KOTH";
		p.Body       = msg;
		p.DurationMs = 5000;
		p.Color      = 3447003;
		ScriptRPC rpc = new ScriptRPC();
		rpc.Write(p);
		rpc.Send(to, ERPCsKOTH.NOTIFY, true, to.GetIdentity());
	}
}
