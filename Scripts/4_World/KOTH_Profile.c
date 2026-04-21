// -----------------------------------------------------------------------------
//  KOTH_Profile - loads/saves all JSON profile files from
//    $profile:PackFazupix\KOTH\
//
//  Responsibilities:
//    - Ensure the profile directory exists.
//    - Write example / default files on first boot.
//    - Deserialise each file into typed objects.
//    - Re-read files on hot-reload tick and only fire the changed callbacks.
// -----------------------------------------------------------------------------

class KOTH_Profile
{
	protected ref KOTH_Settings        m_Settings;
	protected ref KOTH_ZonesFile       m_Zones;
	protected ref KOTH_LootFile        m_Loot;
	protected ref KOTH_Messages        m_Messages;
	protected ref KOTH_WebhookConfig   m_Webhook;

	protected int m_SettingsHash;
	protected int m_ZonesHash;
	protected int m_LootHash;
	protected int m_MessagesHash;
	protected int m_WebhookHash;

	ref ScriptInvoker OnSettingsChanged = new ScriptInvoker();
	ref ScriptInvoker OnZonesChanged    = new ScriptInvoker();
	ref ScriptInvoker OnLootChanged     = new ScriptInvoker();
	ref ScriptInvoker OnMessagesChanged = new ScriptInvoker();
	ref ScriptInvoker OnWebhookChanged  = new ScriptInvoker();

	void KOTH_Profile()
	{
		m_Settings = new KOTH_Settings();
		m_Zones    = new KOTH_ZonesFile();
		m_Zones.Zones = new array<ref KOTH_Zone>();
		m_Loot     = new KOTH_LootFile();
		m_Loot.Tiers = new array<ref KOTH_LootTier>();
		m_Messages = new KOTH_Messages();
		m_Webhook  = new KOTH_WebhookConfig();
	}

	KOTH_Settings      Settings() { return m_Settings; }
	KOTH_ZonesFile     Zones()    { return m_Zones; }
	KOTH_LootFile      Loot()     { return m_Loot; }
	KOTH_Messages      Messages() { return m_Messages; }
	KOTH_WebhookConfig Webhook()  { return m_Webhook; }

	//! Ensures $profile:PackFazupix\KOTH\ exists and that the five JSON files
	//! are present (writes sane defaults/examples when missing).
	void EnsureFiles()
	{
		string dir = KOTH_Const.PROFILE_DIR;
		if (!FileExist(dir))
		{
			MakeDirectory(dir);
			KOTH_Log.Info("Created profile directory " + dir);
		}

		EnsureFile(dir + KOTH_Const.FILE_SETTINGS, m_Settings);
		EnsureZonesFile (dir + KOTH_Const.FILE_ZONES);
		EnsureLootFile  (dir + KOTH_Const.FILE_LOOT);
		EnsureFile(dir + KOTH_Const.FILE_MESSAGES, m_Messages);
		EnsureFile(dir + KOTH_Const.FILE_WEBHOOK , m_Webhook);
	}

	protected void EnsureFile(string path, Class defaults)
	{
		if (FileExist(path)) return;
		JsonFileLoader<Class>.JsonSaveFile(path, defaults);
		KOTH_Log.Info("Wrote default " + path);
	}

	protected void EnsureZonesFile(string path)
	{
		if (FileExist(path)) return;

		// Seed with a representative Chernarus rotation so the admin has a
		// working starting point. They can add/remove/rename freely.
		KOTH_ZonesFile file = new KOTH_ZonesFile();
		file.Zones = new array<ref KOTH_Zone>();

		file.Zones.Insert(MakeZone("nwaf"       , "NW Airfield (ATC)" , 4875  , 0 ,  9545 , 180, 1, 4));
		file.Zones.Insert(MakeZone("tisy"       , "Tisy Military Base", 1530  , 0 , 13100 , 160, 2, 4));
		file.Zones.Insert(MakeZone("kamensk"    , "Kamensk Barracks"  , 7180  , 0 , 14440 , 160, 2, 4));
		file.Zones.Insert(MakeZone("svetloyarsk", "Svetloyarsk Docks" ,13500  , 0 , 13370 , 140, 1, 3));
		file.Zones.Insert(MakeZone("balota"     , "Balota Airfield"   , 4830  , 0 ,  2410 , 150, 1, 3));
		file.Zones.Insert(MakeZone("krasno"     , "Krasnostav Airfield",11935 , 0 , 12385 , 150, 1, 3));
		file.Zones.Insert(MakeZone("zelenogorsk", "Zelenogorsk Base"  , 2800  , 0 ,  5240 , 140, 1, 2));
		file.Zones.Insert(MakeZone("vybor"      , "Vybor Base"        , 3820  , 0 ,  8620 , 150, 1, 3));

		JsonFileLoader<KOTH_ZonesFile>.JsonSaveFile(path, file);
		KOTH_Log.Info("Wrote default " + path + " with " + file.Zones.Count() + " Chernarus zones");
	}

	protected KOTH_Zone MakeZone(string id, string name, float x, float y, float zz, float r, int tmin, int tmax)
	{
		KOTH_Zone z = new KOTH_Zone();
		z.Id       = id;
		z.Name     = name;
		z.X        = x;
		z.Y        = y;
		z.Z        = zz;
		z.Radius   = r;
		z.Enabled  = true;
		z.TierMin  = tmin;
		z.TierMax  = tmax;
		z.Schedule = new array<string>();
		return z;
	}

	protected void EnsureLootFile(string path)
	{
		if (FileExist(path)) return;

		KOTH_LootFile file = new KOTH_LootFile();
		file.Tiers = new array<ref KOTH_LootTier>();

		// Four tiers, weighted to give the "sometimes good, sometimes bad"
		// dynamic the user asked for. Classnames chosen from the supplied
		// modlist are commented where relevant so the admin can edit in place.
		file.Tiers.Insert(MakeTierTrash());
		file.Tiers.Insert(MakeTierCommon());
		file.Tiers.Insert(MakeTierRare());
		file.Tiers.Insert(MakeTierLegendary());

		JsonFileLoader<KOTH_LootFile>.JsonSaveFile(path, file);
		KOTH_Log.Info("Wrote default " + path + " with 4 loot tiers");
	}

	protected KOTH_LootTier MakeTierTrash()
	{
		KOTH_LootTier t = new KOTH_LootTier();
		t.Tier   = 1;
		t.Label  = "Tier 1 - Trash";
		t.Weight = 40;
		t.Kits   = new array<ref KOTH_LootKit>();
		t.Kits.Insert(MakeKit("PlayerVanilla", {
			MakeItem("AKM", 1, 1, 100),
			MakeItem("Mag_AKM_30Rnd", 2, 3, 100),
			MakeItem("TunaCan", 1, 1, 100),
			MakeItem("WaterBottle", 1, 1, 100)
		}));
		return t;
	}

	protected KOTH_LootTier MakeTierCommon()
	{
		KOTH_LootTier t = new KOTH_LootTier();
		t.Tier   = 2;
		t.Label  = "Tier 2 - Common";
		t.Weight = 30;
		t.Kits   = new array<ref KOTH_LootKit>();
		t.Kits.Insert(MakeKit("Mosin_Loadout", {
			MakeItem("Mosin9130", 1, 1, 100),
			MakeItem("Ammo_762x54", 40, 60, 100),
			MakeItem("PU_ScopeOptic", 1, 1, 100),
			MakeItem("SpaghettiCan", 1, 1, 100)
		}));
		t.Kits.Insert(MakeKit("M4_Starter", {
			MakeItem("M4A1", 1, 1, 100),
			MakeItem("Mag_STANAG_30Rnd", 3, 4, 100),
			MakeItem("ACOGOptic", 1, 1, 80)
		}));
		return t;
	}

	protected KOTH_LootTier MakeTierRare()
	{
		KOTH_LootTier t = new KOTH_LootTier();
		t.Tier   = 3;
		t.Label  = "Tier 3 - Rare";
		t.Weight = 20;
		t.Kits   = new array<ref KOTH_LootKit>();
		t.Kits.Insert(MakeKit("Paragon_Rifle", {
			// NOTE: replace with real classnames from @Paragon-Arsenal as needed.
			MakeItem("SVD", 1, 1, 100),
			MakeItem("Mag_SVD_10Rnd", 3, 5, 100),
			MakeItem("PSO1Optic", 1, 1, 100),
			MakeItem("PlateCarrierVest", 1, 1, 100)
		}));
		t.Kits.Insert(MakeKit("SNAFU_MedBox", {
			// NOTE: classnames from @SNAFU-Weapons / @BallerZ-SNAFU-Weapons.
			MakeItem("G36", 1, 1, 100),
			MakeItem("Mag_G36_30Rnd", 4, 6, 100),
			MakeItem("TacticalBaconCan", 4, 6, 100),
			MakeItem("BandageDressing", 5, 10, 100)
		}));
		return t;
	}

	protected KOTH_LootTier MakeTierLegendary()
	{
		KOTH_LootTier t = new KOTH_LootTier();
		t.Tier   = 4;
		t.Label  = "Tier 4 - Legendary";
		t.Weight = 10;
		t.Kits   = new array<ref KOTH_LootKit>();
		t.Kits.Insert(MakeKit("Juggernaut_Loadout", {
			// NOTE: classnames from @Juggernaut-Armor, @Altyn-helmet, @Matrix-Clothing-Set.
			MakeItem("JuggernautSuit", 1, 1, 100),
			MakeItem("AltynHelmet", 1, 1, 100),
			MakeItem("M249", 1, 1, 100),
			MakeItem("Mag_M249_200Rnd", 2, 3, 100)
		}));
		t.Kits.Insert(MakeKit("Elite_Airdrop", {
			MakeItem("M107", 1, 1, 100),
			MakeItem("Mag_M107_10Rnd", 3, 5, 100),
			MakeItem("GhillieSuit_Mossy", 1, 1, 100),
			MakeItem("Morphine", 5, 10, 100)
		}));
		return t;
	}

	protected KOTH_LootKit MakeKit(string name, array<ref KOTH_LootItem> items)
	{
		KOTH_LootKit k = new KOTH_LootKit();
		k.Name  = name;
		k.Items = items;
		return k;
	}

	protected KOTH_LootItem MakeItem(string cls, int mn, int mx, int chance)
	{
		KOTH_LootItem it = new KOTH_LootItem();
		it.ClassName = cls;
		it.Min       = mn;
		it.Max       = mx;
		it.Chance    = chance;
		it.Attachments = new array<string>();
		it.Cargo       = new array<string>();
		return it;
	}

	// ------------------------------------------------------------------
	// Loading (initial + hot-reload)
	// ------------------------------------------------------------------

	void LoadAll()
	{
		LoadSettings();
		LoadZones();
		LoadLoot();
		LoadMessages();
		LoadWebhook();
		KOTH_Log.SetLevel(m_Settings.LogLevel);
	}

	void LoadSettings()
	{
		KOTH_Settings next = new KOTH_Settings();
		if (JsonFileLoader<KOTH_Settings>.LoadFile(KOTH_Const.PROFILE_DIR + KOTH_Const.FILE_SETTINGS, next))
		{
			int hash = HashOf(next);
			if (hash != m_SettingsHash)
			{
				m_Settings     = next;
				m_SettingsHash = hash;
				KOTH_Log.SetLevel(m_Settings.LogLevel);
				OnSettingsChanged.Invoke();
				KOTH_Log.Info("settings.json (re)loaded");
			}
		}
	}

	void LoadZones()
	{
		KOTH_ZonesFile next = new KOTH_ZonesFile();
		if (JsonFileLoader<KOTH_ZonesFile>.LoadFile(KOTH_Const.PROFILE_DIR + KOTH_Const.FILE_ZONES, next))
		{
			if (!next.Zones) next.Zones = new array<ref KOTH_Zone>();
			int hash = HashOf(next);
			if (hash != m_ZonesHash)
			{
				m_Zones      = next;
				m_ZonesHash  = hash;
				OnZonesChanged.Invoke();
				KOTH_Log.Info("zones.json (re)loaded: " + next.Zones.Count() + " zones");
			}
		}
	}

	void LoadLoot()
	{
		KOTH_LootFile next = new KOTH_LootFile();
		if (JsonFileLoader<KOTH_LootFile>.LoadFile(KOTH_Const.PROFILE_DIR + KOTH_Const.FILE_LOOT, next))
		{
			if (!next.Tiers) next.Tiers = new array<ref KOTH_LootTier>();
			int hash = HashOf(next);
			if (hash != m_LootHash)
			{
				m_Loot      = next;
				m_LootHash  = hash;
				OnLootChanged.Invoke();
				KOTH_Log.Info("loot_tiers.json (re)loaded: " + next.Tiers.Count() + " tiers");
			}
		}
	}

	void LoadMessages()
	{
		KOTH_Messages next = new KOTH_Messages();
		if (JsonFileLoader<KOTH_Messages>.LoadFile(KOTH_Const.PROFILE_DIR + KOTH_Const.FILE_MESSAGES, next))
		{
			int hash = HashOf(next);
			if (hash != m_MessagesHash)
			{
				m_Messages     = next;
				m_MessagesHash = hash;
				OnMessagesChanged.Invoke();
				KOTH_Log.Info("messages.json (re)loaded");
			}
		}
	}

	void LoadWebhook()
	{
		KOTH_WebhookConfig next = new KOTH_WebhookConfig();
		if (JsonFileLoader<KOTH_WebhookConfig>.LoadFile(KOTH_Const.PROFILE_DIR + KOTH_Const.FILE_WEBHOOK, next))
		{
			int hash = HashOf(next);
			if (hash != m_WebhookHash)
			{
				m_Webhook     = next;
				m_WebhookHash = hash;
				OnWebhookChanged.Invoke();
				KOTH_Log.Info("webhook.json (re)loaded (enabled=" + next.Enabled + ")");
			}
		}
	}

	//! Cheap content-based signature. Enforce doesn't expose a real hash, so
	//! we serialise the object back to JSON and hash the resulting string.
	protected int HashOf(Class obj)
	{
		string buf;
		JsonSerializer js = new JsonSerializer();
		js.WriteToString(obj, false, buf);
		return buf.Hash();
	}
}
