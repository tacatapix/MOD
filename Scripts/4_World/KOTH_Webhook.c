// -----------------------------------------------------------------------------
//  KOTH_Webhook - optimised Discord webhook client.
//
//  DayZ's RestApi is async-friendly but naive mods call it once per event,
//  which crashes head-first into Discord's 30 req/min rate limits and stalls
//  the mission thread while connections pile up. Instead we:
//
//    * Keep an in-memory queue of embeds.
//    * Flush at most `BatchSize` embeds per POST (Discord's hard cap is 10).
//    * Flush on a timer (`FlushIntervalSec`) rather than on every event.
//    * Drop oldest entries when the queue exceeds `MaxQueueSize` so we never
//      leak memory if the webhook endpoint is down for a long time.
//    * Do all HTTP work from RestContext callbacks - the main thread never
//      blocks on the network.
// -----------------------------------------------------------------------------

class KOTH_WebhookEmbed
{
	string Title;
	string Description;
	int    Color;
	string Timestamp;  // ISO8601
	ref array<ref KOTH_WebhookField> Fields;
}

class KOTH_WebhookField
{
	string name;
	string value;
	bool   inline;
}

class KOTH_WebhookPayload
{
	string                                username;
	string                                avatar_url;
	ref array<ref KOTH_WebhookEmbed>      embeds;
}

class KOTH_WebhookCallback : RestCallback
{
	override void OnSuccess(string data, int dataSize)
	{
		KOTH_Log.Debug("[webhook] POST ok (" + dataSize + "b)");
	}

	override void OnError(int errorCode)
	{
		KOTH_Log.Warn("[webhook] POST failed, code=" + errorCode);
	}

	override void OnTimeout()
	{
		KOTH_Log.Warn("[webhook] POST timeout");
	}
}

class KOTH_Webhook
{
	protected KOTH_WebhookConfig                m_Cfg;
	protected ref array<ref KOTH_WebhookEmbed>  m_Queue;
	protected ref KOTH_WebhookCallback          m_Cb;
	protected int                               m_NextFlushMs;

	void KOTH_Webhook()
	{
		m_Queue = new array<ref KOTH_WebhookEmbed>();
		m_Cb    = new KOTH_WebhookCallback();
	}

	void SetConfig(KOTH_WebhookConfig cfg)
	{
		m_Cfg = cfg;
	}

	// ----- Enqueue helpers -------------------------------------------------

	void Announce(string zoneName, int secondsUntilStart)
	{
		if (!m_Cfg || !m_Cfg.Enabled || !m_Cfg.SendAnnounce) return;
		Enqueue(Embed("KOTH - evento anunciado",
			"Zona: **" + zoneName + "**\nInicia em **" + secondsUntilStart + "s**",
			m_Cfg.ColorAnnounce));
	}

	void Started(string zoneName)
	{
		if (!m_Cfg || !m_Cfg.Enabled || !m_Cfg.SendStart) return;
		Enqueue(Embed("KOTH - evento iniciado",
			"Zona: **" + zoneName + "**",
			m_Cfg.ColorStart));
	}

	void CaptureBegin(string zoneName, string player, int playersInZone)
	{
		if (!m_Cfg || !m_Cfg.Enabled || !m_Cfg.SendCaptureBegin) return;
		KOTH_WebhookEmbed e = Embed("KOTH - captura iniciada",
			"Zona: **" + zoneName + "**\nJogador: **" + player + "**",
			m_Cfg.ColorCaptureBegin);
		AddField(e, "Jogadores na zona", playersInZone.ToString(), true);
		Enqueue(e);
	}

	void Captured(string zoneName, string player, string tierLabel, string kitName)
	{
		if (!m_Cfg || !m_Cfg.Enabled || !m_Cfg.SendCaptured) return;
		KOTH_WebhookEmbed e = Embed("KOTH - zona capturada",
			"Zona: **" + zoneName + "**\nVencedor: **" + player + "**",
			m_Cfg.ColorCaptured);
		AddField(e, "Tier",  tierLabel, true);
		AddField(e, "Kit",   kitName,   true);
		Enqueue(e);
	}

	void Ended(string zoneName)
	{
		if (!m_Cfg || !m_Cfg.Enabled || !m_Cfg.SendEnded) return;
		Enqueue(Embed("KOTH - evento encerrado",
			"Zona: **" + zoneName + "**",
			m_Cfg.ColorEnded));
	}

	// ----- Flush timer -----------------------------------------------------

	//! Called from the manager tick. We use a local ms counter instead of
	//! GetGame().GetTickTime() to avoid pulling in a mission-bound API in
	//! case this is reused from server-only code.
	void Tick(int deltaMs)
	{
		if (!m_Cfg || !m_Cfg.Enabled) { m_Queue.Clear(); return; }
		m_NextFlushMs -= deltaMs;
		if (m_NextFlushMs > 0) return;
		m_NextFlushMs = m_Cfg.FlushIntervalSec * 1000;
		Flush();
	}

	void Flush()
	{
		if (!m_Cfg || !m_Cfg.Enabled || m_Queue.Count() == 0) return;
		if (m_Cfg.Url == "")                                  return;

		int batch = m_Cfg.BatchSize;
		if (batch > 10) batch = 10;  // Discord hard cap
		if (batch < 1)  batch = 1;

		int n = m_Queue.Count();
		if (n > batch) n = batch;

		KOTH_WebhookPayload p = new KOTH_WebhookPayload();
		p.username   = m_Cfg.Username;
		p.avatar_url = m_Cfg.AvatarUrl;
		p.embeds     = new array<ref KOTH_WebhookEmbed>();
		for (int i = 0; i < n; i++) p.embeds.Insert(m_Queue[i]);
		for (int j = 0; j < n; j++) m_Queue.Remove(0);

		string body;
		JsonSerializer js = new JsonSerializer();
		js.WriteToString(p, false, body);

		RestContext ctx = GetRestApi().GetRestContext(m_Cfg.Url);
		if (!ctx)
		{
			KOTH_Log.Warn("[webhook] RestContext null - skipping flush");
			return;
		}
		ctx.SetHeader("application/json");
		// Async POST - RestContext fires back through our RestCallback. The
		// main thread never blocks on network I/O.
		ctx.POST(m_Cb, "", body);
	}

	// ----- Internals -------------------------------------------------------

	protected KOTH_WebhookEmbed Embed(string title, string desc, int color)
	{
		KOTH_WebhookEmbed e = new KOTH_WebhookEmbed();
		e.Title       = title;
		e.Description = desc;
		e.Color       = color;
		e.Fields      = new array<ref KOTH_WebhookField>();
		// Enforce doesn't ship an ISO formatter - we emit a best-effort value
		// using the in-game clock. Discord ignores bad timestamps silently.
		int y, m, d, h, mi, s;
		GetYearMonthDay(y, m, d);
		GetHourMinuteSecond(h, mi, s);
		e.Timestamp = "" + y + "-" + Pad(m) + "-" + Pad(d) + "T" + Pad(h) + ":" + Pad(mi) + ":" + Pad(s) + "Z";
		return e;
	}

	protected void AddField(KOTH_WebhookEmbed e, string name, string value, bool inl)
	{
		KOTH_WebhookField f = new KOTH_WebhookField();
		f.name   = name;
		f.value  = value;
		f.inline = inl;
		e.Fields.Insert(f);
	}

	protected string Pad(int v)
	{
		if (v < 10) return "0" + v.ToString();
		return v.ToString();
	}

	protected void Enqueue(KOTH_WebhookEmbed e)
	{
		m_Queue.Insert(e);
		while (m_Queue.Count() > m_Cfg.MaxQueueSize)
			m_Queue.Remove(0);
	}
}
