// -----------------------------------------------------------------------------
//  KOTH_HUD - client-side HUD: capture bar, player-count, toast messages.
//
//  Rendered from PackFazupix_KOTH/GUI/layouts/KOTH/capture_hud.layout.
//  The HUD is only shown when the player is within the capture radius of
//  an active zone, or when a zone is in ANNOUNCED/ACTIVE state (so the
//  player sees the "N minutes until start" overlay).
// -----------------------------------------------------------------------------

class KOTH_HUDToast
{
	string Title;
	string Body;
	int    Color;
	int    RemainingMs;
}

class KOTH_HUD
{
	protected Widget        m_Root;
	protected Widget        m_Panel;
	protected TextWidget    m_TitleText;
	protected TextWidget    m_StatusText;
	protected TextWidget    m_CountText;
	protected TextWidget    m_TimerText;
	protected ProgressBarWidget m_ProgressBar;

	protected Widget        m_ToastRoot;
	protected TextWidget    m_ToastTitle;
	protected TextWidget    m_ToastBody;
	protected int           m_ToastMsLeft;

	protected ref KOTH_StatePayload m_LastState;

	void KOTH_HUD()
	{
		m_Root = GetGame().GetWorkspace().CreateWidgets("PackFazupix_KOTH/GUI/layouts/KOTH/capture_hud.layout");
		if (!m_Root) { Print("[KOTH][HUD] could not load layout"); return; }

		m_Panel       = m_Root.FindAnyWidget("KOTH_CapturePanel");
		m_TitleText   = TextWidget.Cast(m_Root.FindAnyWidget("KOTH_Title"));
		m_StatusText  = TextWidget.Cast(m_Root.FindAnyWidget("KOTH_Status"));
		m_CountText   = TextWidget.Cast(m_Root.FindAnyWidget("KOTH_Count"));
		m_TimerText   = TextWidget.Cast(m_Root.FindAnyWidget("KOTH_Timer"));
		m_ProgressBar = ProgressBarWidget.Cast(m_Root.FindAnyWidget("KOTH_Progress"));

		m_ToastRoot   = m_Root.FindAnyWidget("KOTH_Toast");
		m_ToastTitle  = TextWidget.Cast(m_Root.FindAnyWidget("KOTH_ToastTitle"));
		m_ToastBody   = TextWidget.Cast(m_Root.FindAnyWidget("KOTH_ToastBody"));

		Hide();

		GetGame().GetUpdateQueue(CALL_CATEGORY_GUI).Insert(OnFrame);
	}

	void ~KOTH_HUD()
	{
		GetGame().GetUpdateQueue(CALL_CATEGORY_GUI).Remove(OnFrame);
		if (m_Root) m_Root.Unlink();
	}

	void Show()
	{
		if (m_Root) m_Root.Show(true);
		if (m_Panel) m_Panel.Show(false);
		if (m_ToastRoot) m_ToastRoot.Show(false);
	}

	void Hide()
	{
		if (m_Root) m_Root.Show(false);
	}

	// ------------------------------------------------------------------
	// RPC handlers
	// ------------------------------------------------------------------

	void OnStateSync(KOTH_StatePayload s)
	{
		m_LastState = s;
		RenderState();
	}

	void OnNotify(KOTH_NotifyPayload n)
	{
		if (!m_ToastRoot) return;
		m_ToastTitle.SetText(n.Title);
		m_ToastBody.SetText(n.Body);
		m_ToastRoot.Show(true);
		m_ToastMsLeft = n.DurationMs;
		if (m_ToastMsLeft <= 0) m_ToastMsLeft = 5000;
	}

	// ------------------------------------------------------------------
	// Rendering
	// ------------------------------------------------------------------

	protected void OnFrame(float dtSeconds)
	{
		int dtMs = (int)(dtSeconds * 1000);

		if (m_ToastMsLeft > 0)
		{
			m_ToastMsLeft -= dtMs;
			if (m_ToastMsLeft <= 0 && m_ToastRoot) m_ToastRoot.Show(false);
		}
	}

	protected void RenderState()
	{
		if (!m_Panel || !m_LastState) return;

		PlayerBase me = PlayerBase.Cast(GetGame().GetPlayer());
		bool inZone = false;
		if (me)
		{
			vector p = me.GetPosition();
			float dx = p[0] - m_LastState.ZonePos[0];
			float dz = p[2] - m_LastState.ZonePos[2];
			inZone = (dx * dx + dz * dz) <= (m_LastState.ZoneRadius * m_LastState.ZoneRadius);
		}

		// Visibility policy:
		//   - ACTIVE: show to everyone so the whole server knows a capture
		//             is happening (matches the user's requirement to warn
		//             all players on capture start).
		//   - ANNOUNCED: show only to players inside or very close (HUD
		//                stays clean for everyone else).
		//   - CAPTURED: brief flash for all.
		//   - IDLE / COOLDOWN: hide.
		bool show = false;
		switch (m_LastState.State)
		{
			case KOTH_Const.STATE_ANNOUNCED: show = inZone;  break;
			case KOTH_Const.STATE_ACTIVE:    show = true;    break;
			case KOTH_Const.STATE_CAPTURED:  show = true;    break;
			default:                         show = false;   break;
		}
		m_Panel.Show(show);
		if (!show) return;

		m_TitleText.SetText(m_LastState.ZoneName);

		if (m_LastState.State == KOTH_Const.STATE_ANNOUNCED)
			m_StatusText.SetText("Inicia em " + m_LastState.SecondsRemaining + "s");
		else if (m_LastState.Contested)
			m_StatusText.SetText("CONTESTADO");
		else if (m_LastState.Capturer != "")
			m_StatusText.SetText("Capturando: " + m_LastState.Capturer);
		else if (m_LastState.State == KOTH_Const.STATE_CAPTURED)
			m_StatusText.SetText("CAPTURADO!");
		else
			m_StatusText.SetText("Aguardando capturadores");

		m_CountText.SetText("Jogadores na zona: " + m_LastState.PlayersInZone);
		m_TimerText.SetText(FormatTimer(m_LastState.SecondsRemaining));

		if (m_ProgressBar)
		{
			float pct = m_LastState.ProgressPct;
			if (pct < 0) pct = 0;
			if (pct > 1) pct = 1;
			m_ProgressBar.SetCurrent(pct * 100.0);
		}
	}

	protected string FormatTimer(int seconds)
	{
		if (seconds <= 0) return "00:00";
		int m = seconds / 60;
		int s = seconds - m * 60;
		string sm = m.ToString(); if (m < 10) sm = "0" + sm;
		string ss = s.ToString(); if (s < 10) ss = "0" + ss;
		return sm + ":" + ss;
	}
}
