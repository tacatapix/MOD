// -----------------------------------------------------------------------------
//  KOTH_LootTier - tier/kit configuration loaded from loot_tiers.json
//
//  The file contains exactly four tiers (1..4). Each tier is a pool of
//  "kits". When a player captures a zone, the server:
//    1. Rolls a tier using the Weight field of each tier (higher = more
//       common). This gives the dynamic of "sometimes you get good loot,
//       sometimes not" that the user asked for.
//    2. Picks a kit from that tier uniformly at random.
//    3. Spawns the items in that kit on the ground inside the zone.
// -----------------------------------------------------------------------------

class KOTH_LootItem
{
	string ClassName  = "";
	int    Min        = 1;
	int    Max        = 1;
	//! 0..100 probability (100 = always spawn when this kit is selected).
	int    Chance     = 100;
	//! Optional attachment classnames (e.g. a scope on a rifle).
	ref array<string> Attachments;
	//! Optional cargo classnames (items placed inside this item's cargo).
	ref array<string> Cargo;
}

class KOTH_LootKit
{
	string Name       = "";
	ref array<ref KOTH_LootItem> Items;
}

class KOTH_LootTier
{
	int    Tier       = 1;        // 1..4
	string Label      = "Tier 1"; // used in webhook / HUD
	int    Weight     = 40;       // relative roll weight
	ref array<ref KOTH_LootKit> Kits;
}

class KOTH_LootFile
{
	ref array<ref KOTH_LootTier> Tiers;
}
