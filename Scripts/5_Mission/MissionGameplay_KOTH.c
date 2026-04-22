// -----------------------------------------------------------------------------
//  MissionGameplay_KOTH - client-side wiring.
//
//  Responsibilities:
//    - Create the HUD when the mission starts.
//    - Route incoming RPCs (SYNC_STATE, NOTIFY) to the HUD.
// -----------------------------------------------------------------------------

modded class MissionGameplay
{
	protected ref KOTH_HUD m_KOTH_HUD;

	override void OnInit()
	{
		super.OnInit();
		if (!m_KOTH_HUD) m_KOTH_HUD = new KOTH_HUD();
	}

	override void OnMissionStart()
	{
		super.OnMissionStart();
		if (m_KOTH_HUD) m_KOTH_HUD.Show();
	}

	override void OnMissionFinish()
	{
		if (m_KOTH_HUD) m_KOTH_HUD.Hide();
		super.OnMissionFinish();
	}

	override void OnRPC(PlayerIdentity sender, Object target, int rpc_type, ParamsReadContext ctx)
	{
		super.OnRPC(sender, target, rpc_type, ctx);

		switch (rpc_type)
		{
			case ERPCsKOTH.SYNC_STATE:
			{
				KOTH_StatePayload s = new KOTH_StatePayload();
				if (ctx.Read(s) && m_KOTH_HUD) m_KOTH_HUD.OnStateSync(s);
				break;
			}

			case ERPCsKOTH.NOTIFY:
			{
				KOTH_NotifyPayload n = new KOTH_NotifyPayload();
				if (ctx.Read(n) && m_KOTH_HUD) m_KOTH_HUD.OnNotify(n);
				break;
			}
		}
	}
}
