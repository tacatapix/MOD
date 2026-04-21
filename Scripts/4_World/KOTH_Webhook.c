// -----------------------------------------------------------------------------
//  KOTH_Webhook - optimised Discord webhook client.
//
//  DayZ's RestApi is async-friendly but naive mods call it once per event,
//  which crashes head-first into Discord's 30 req/min rate limits and stalls
//  the mission thread while connections pile up. Instead we:
//
//    * Keep an in-memory FIFO queue of embeds.
//    * Flush at most `BatchSize` embeds per POST (Discord's hard cap is 10).
//    * Flush on a timer (`FlushIntervalSec`) rather than on every event.
//    * Drop oldest entries when the queue exceeds `MaxQueueSize` so we never
//      leak memory if the webhook endpoint is down for a long time.
//    * Do all HTTP work from RestContext callbacks - the main thread never
//      blocks on the network.
//    * In-flight guard: never have more than one POST outstanding, so a slow
//      Discord never causes overlapping requests to pile up.
//    * Retry budget: on OnError / OnTimeout the in-flight batch is re-queued
//      up to `MaxRetries` times; after that the batch is dropped and a
//      metric line is logged so admins can see the webhook is unhealthy.
//    * Exponential backoff on failure, capped at `MaxBackoffSec`. When the
//      endpoint becomes healthy again the backoff resets.
//    * Payload cap: individual embed descriptions are truncated to a safe
//      length so a runaway string can't exceed Discord's 6000-char limit.
//    * Metric counters (`queued / sent / dropped / retried`) periodically
//      logged at INFO level for observability.
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

//! Engine-invoked callback. Holds a back-reference to the owning webhook so
//! we can signal success/failure back into the batching layer. Because the
//! in-flight guard ensures at most one outstanding POST, this is safe.
class KOTH_WebhookCallback : RestCallback
{
	ref KOTH_Webhook_WeakRef Owner;

	override void OnSuccess(string data, int dataSize)
	{
		if (Owner && Owner.Ref) Owner.Ref.OnFlushSuccess(dataSize);
	}
	override void OnError(int errorCode)
	{
		if (Owner && Owner.Ref) Owner.Ref.OnFlushError(errorCode);
	}
	override void OnTimeout()
	{
		if (Owner && Owner.Ref) Owner.Ref.OnFlushTimeout();
	}
}

//! Tiny wrapper so the RestCallback never holds a strong ref to the webhook
//! (would prevent GC if the webhook owner goes away mid-flight).
class KOTH_Webhook_WeakRef
{
	KOTH_Webhook Ref;
}

class KOTH_Webhook
{
	// Tuning constants -----------------------------------------------------
	protected const int DISCORD_EMBED_DESC_CAP    = 3500;  //!< conservative vs. 4096 hard cap
	protected const int METRICS_LOG_EVERY_FLUSHES = 10;    //!< log every N flushes

	// Config + queue -------------------------------------------------------
	protected KOTH_WebhookConfig                m_Cfg;
	protected ref array<ref KOTH_WebhookEmbed>  m_Queue;
	protected ref KOTH_WebhookCallback          m_Cb;
	protected ref KOTH_Webhook_WeakRef          m_WeakRef;

	// Flush scheduling -----------------------------------------------------
	protected int   m_NextFlushMs;
	protected int   m_BackoffMs;        //!< >0 == postpone next flush

	// In-flight state ------------------------------------------------------
	protected bool                              m_InFlight;
	protected int                               m_InFlightRetries;
	protected ref array<ref KOTH_WebhookEmbed>  m_InFlightBatch;

	// Metrics (since process start) ----------------------------------------
	protected int   m_StatQueued;
	protected int   m_StatSent;
	protected int   m_StatDropped;
	protected int   m_StatRetries;
	protected int   m_StatFlushes;

	void KOTH_Webhook()
	{
		m_Queue          = new array<ref KOTH_WebhookEmbed>();
		m_InFlightBatch  = new array<ref KOTH_WebhookEmbed>();
		m_WeakRef        = new KOTH_Webhook_WeakRef();
		m_WeakRef.Ref    = this;
		m_Cb             = new KOTH_WebhookCallback();
		m_Cb.Owner       = m_WeakRef;
	}

	void ~KOTH_Webhook()
	{
		if (m_WeakRef) m_WeakRef.Ref = null;
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

	void CaptureProgress(string zoneName, string player, int playersInZone, int percent)
	{
		if (!m_Cfg || !m_Cfg.Enabled || !m_Cfg.SendCaptureProgress) return;
		KOTH_WebhookEmbed e = Embed("KOTH - captura em andamento",
			"Zona: **" + zoneName + "**\nJogador: **" + player + "** (" + percent + "%)",
			m_Cfg.ColorCaptureBegin);
		AddField(e, "Jogadores na zona", playersInZone.ToString(), true);
		AddField(e, "Progresso", percent.ToString() + "%", true);
		Enqueue(e);
	}

	void Contested(string zoneName, int playersInZone)
	{
		if (!m_Cfg || !m_Cfg.Enabled || !m_Cfg.SendContested) return;
		KOTH_WebhookEmbed e = Embed("KOTH - zona contestada",
			"Zona: **" + zoneName + "**",
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

		// Backoff window: Discord told us to slow down (or we failed).
		if (m_BackoffMs > 0)
		{
			m_BackoffMs -= deltaMs;
			if (m_BackoffMs > 0) return;
		}

		m_NextFlushMs -= deltaMs;
		if (m_NextFlushMs > 0) return;
		m_NextFlushMs = m_Cfg.FlushIntervalSec * 1000;
		Flush();
	}

	void Flush()
	{
		if (!m_Cfg || !m_Cfg.Enabled)     return;
		if (m_InFlight)                    return; //!< guard - a POST is running
		if (m_Queue.Count() == 0)          return;
		if (m_Cfg.Url == "")               return;

		int batch = m_Cfg.BatchSize;
		if (batch > 10) batch = 10;  // Discord hard cap
		if (batch < 1)  batch = 1;

		int n = m_Queue.Count();
		if (n > batch) n = batch;

		// Move the batch from queue to in-flight storage. If the POST fails
		// we re-prepend it on the next Tick so nothing is lost unless the
		// retry budget is exhausted.
		m_InFlightBatch.Clear();
		for (int i = 0; i < n; i++) m_InFlightBatch.Insert(m_Queue[i]);
		for (int j = 0; j < n; j++) m_Queue.Remove(0);

		KOTH_WebhookPayload p = new KOTH_WebhookPayload();
		p.username   = m_Cfg.Username;
		p.avatar_url = m_Cfg.AvatarUrl;
		p.embeds     = new array<ref KOTH_WebhookEmbed>();
		foreach (KOTH_WebhookEmbed eRef : m_InFlightBatch) p.embeds.Insert(eRef);

		string body;
		JsonSerializer js = new JsonSerializer();
		js.WriteToString(p, false, body);

		RestContext ctx = GetRestApi().GetRestContext(m_Cfg.Url);
		if (!ctx)
		{
			KOTH_Log.Warn("[webhook] RestContext null - re-queuing batch");
			RequeueInFlight();
			return;
		}
		ctx.SetHeader("application/json");
		m_InFlight = true;
		ctx.POST(m_Cb, "", body);
	}

	// ----- Callback hooks (invoked from KOTH_WebhookCallback) --------------

	void OnFlushSuccess(int bytes)
	{
		m_StatSent  += m_InFlightBatch.Count();
		m_StatFlushes++;
		m_InFlight   = false;
		m_InFlightRetries = 0;
		m_BackoffMs  = 0; //!< healthy again - reset
		m_InFlightBatch.Clear();
		KOTH_Log.Debug("[webhook] POST ok (" + bytes + "b)");
		MaybeLogMetrics();
	}

	void OnFlushError(int code)
	{
		HandleFailure("error code=" + code, code);
	}

	void OnFlushTimeout()
	{
		HandleFailure("timeout", -1);
	}

	// ----- Internals -------------------------------------------------------

	protected void HandleFailure(string reason, int code)
	{
		m_InFlight = false;
		m_InFlightRetries++;
		m_StatRetries++;

		bool retryable = (code != 400 && code != 401 && code != 403 && code != 404);

		if (retryable && m_InFlightRetries <= m_Cfg.MaxRetries)
		{
			// Re-prepend the in-flight batch so FIFO order is preserved on
			// the next flush, then apply exponential backoff.
			RequeueInFlight();
			int backoff = 1;
			for (int i = 0; i < m_InFlightRetries; i++) backoff *= 2;
			if (backoff > m_Cfg.MaxBackoffSec) backoff = m_Cfg.MaxBackoffSec;
			m_BackoffMs = backoff * 1000;
			KOTH_Log.Warn("[webhook] POST failed (" + reason + ") - retry "
				+ m_InFlightRetries + "/" + m_Cfg.MaxRetries
				+ " in " + backoff + "s");
		}
		else
		{
			// Give up on this batch.
			int dropped = m_InFlightBatch.Count();
			m_StatDropped += dropped;
			m_InFlightBatch.Clear();
			m_InFlightRetries = 0;
			KOTH_Log.Error("[webhook] POST permanently failed (" + reason
				+ ") - dropped " + dropped + " embed(s)");
		}
		MaybeLogMetrics();
	}

	protected void RequeueInFlight()
	{
		// Insert at the front so retried embeds go out before newer ones.
		for (int i = m_InFlightBatch.Count() - 1; i >= 0; i--)
		{
			m_Queue.InsertAt(m_InFlightBatch[i], 0);
		}
		m_InFlightBatch.Clear();
		m_InFlight = false;
	}

	protected void MaybeLogMetrics()
	{
		if (m_StatFlushes == 0) return;
		if (m_StatFlushes % METRICS_LOG_EVERY_FLUSHES != 0) return;
		KOTH_Log.Info("[webhook] metrics queued=" + m_StatQueued
			+ " sent=" + m_StatSent
			+ " dropped=" + m_StatDropped
			+ " retries=" + m_StatRetries
			+ " flushes=" + m_StatFlushes);
	}

	protected KOTH_WebhookEmbed Embed(string title, string desc, int color)
	{
		KOTH_WebhookEmbed e = new KOTH_WebhookEmbed();
		e.Title       = title;
		e.Description = TruncateDesc(desc);
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

	protected string TruncateDesc(string s)
	{
		if (s.Length() <= DISCORD_EMBED_DESC_CAP) return s;
		return s.Substring(0, DISCORD_EMBED_DESC_CAP - 4) + "...";
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
		m_StatQueued++;
		while (m_Queue.Count() > m_Cfg.MaxQueueSize)
		{
			m_Queue.Remove(0);
			m_StatDropped++;
		}
	}
}
