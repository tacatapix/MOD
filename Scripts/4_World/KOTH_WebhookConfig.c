// -----------------------------------------------------------------------------
//  KOTH_WebhookConfig - loaded from profiles\PackFazupix\KOTH\webhook.json
//
//  The webhook is "optimized": instead of making a separate HTTP POST per
//  event it queues embeds and flushes them every FlushIntervalSec so that
//  Discord rate-limits never block the main thread. See KOTH_Webhook.c.
// -----------------------------------------------------------------------------

class KOTH_WebhookConfig
{
	//! If false all webhook calls are no-ops.
	bool   Enabled              = false;

	//! Full Discord webhook URL - keep this out of version control.
	string Url                  = "";

	//! Username shown in Discord.
	string Username             = "KOTH";

	//! Avatar URL shown in Discord.
	string AvatarUrl            = "";

	//! Embed accent colours per event type (decimal RGB).
	int    ColorAnnounce        = 3447003; // blue
	int    ColorStart           = 3066993; // green
	int    ColorCaptureBegin    = 15844367;// gold
	int    ColorCaptured        = 15158332;// red
	int    ColorEnded           = 9807270; // grey

	//! Max embeds per HTTP POST. Discord hard cap is 10.
	int    BatchSize            = 10;

	//! How often the queue is flushed (seconds).
	int    FlushIntervalSec     = 5;

	//! If the queue grows beyond this the oldest embeds are dropped to avoid
	//! unbounded memory growth when Discord is down.
	int    MaxQueueSize         = 200;

	//! Which event types to forward to Discord.
	bool   SendAnnounce         = true;
	bool   SendStart            = true;
	bool   SendCaptureBegin     = true;
	bool   SendCaptured         = true;
	bool   SendEnded            = true;
}
