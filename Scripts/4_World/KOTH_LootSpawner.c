// -----------------------------------------------------------------------------
//  KOTH_LootSpawner - rolls a tier & kit then spawns the items in the world.
//
//  The roll is weighted by KOTH_LootTier.Weight to create the dynamic the
//  user asked for ("sometimes good loot, sometimes bad"). Inside a tier,
//  kits are picked uniformly at random.
// -----------------------------------------------------------------------------

class KOTH_LootRollResult
{
	ref KOTH_LootTier Tier;
	ref KOTH_LootKit  Kit;
}

class KOTH_LootSpawner
{
	//! Picks a tier by weight then a kit inside that tier. Returns null if
	//! the loot file is empty. Tier/Kit in the result are direct references
	//! into the loot file - do NOT mutate them.
	static KOTH_LootRollResult Roll(KOTH_LootFile file, int minTier = 1, int maxTier = 4)
	{
		if (!file || !file.Tiers || file.Tiers.Count() == 0) return null;

		// Filter tiers to the allowed range and sum weights.
		int total = 0;
		array<KOTH_LootTier> pool = new array<KOTH_LootTier>();
		foreach (KOTH_LootTier t : file.Tiers)
		{
			if (t.Tier < minTier || t.Tier > maxTier) continue;
			if (!t.Kits || t.Kits.Count() == 0)       continue;
			if (t.Weight <= 0)                        continue;
			pool.Insert(t);
			total += t.Weight;
		}
		if (pool.Count() == 0 || total <= 0) return null;

		int roll = Math.RandomIntInclusive(1, total);
		KOTH_LootTier picked;
		int acc = 0;
		foreach (KOTH_LootTier t2 : pool)
		{
			acc += t2.Weight;
			if (roll <= acc) { picked = t2; break; }
		}
		if (!picked) picked = pool[pool.Count() - 1];

		KOTH_LootKit kit = picked.Kits[Math.RandomInt(0, picked.Kits.Count())];

		KOTH_LootRollResult res = new KOTH_LootRollResult();
		res.Tier = picked;
		res.Kit  = kit;
		return res;
	}

	//! Spawns every item in the kit on the ground around `center` within
	//! `spread` metres. Returns the number of entities actually spawned.
	static int SpawnKit(KOTH_LootKit kit, vector center, float spread, int lifetimeSec)
	{
		if (!kit || !kit.Items) return 0;
		int spawned = 0;

		foreach (KOTH_LootItem it : kit.Items)
		{
			if (it.Chance < 100 && Math.RandomIntInclusive(1, 100) > it.Chance)
				continue;

			int qty = Math.RandomIntInclusive(it.Min, it.Max);
			if (qty < 1) qty = 1;

			for (int i = 0; i < qty; i++)
			{
				vector pos = RandomOffset(center, spread);
				EntityAI e = EntityAI.Cast(GetGame().CreateObjectEx(it.ClassName, pos, ECE_PLACE_ON_SURFACE));
				if (!e)
				{
					KOTH_Log.Warn("Loot classname not found: " + it.ClassName);
					continue;
				}
				SetupItem(e);
				AttachAttachments(e, it.Attachments);
				FillCargo(e, it.Cargo);
				ScheduleCleanup(e, lifetimeSec);
				spawned++;
			}
		}
		KOTH_Log.Info("Spawned " + spawned + " items from kit '" + kit.Name + "' at " + center.ToString());
		return spawned;
	}

	protected static vector RandomOffset(vector center, float spread)
	{
		float a = Math.RandomFloat(0, Math.PI2);
		float r = Math.RandomFloat(0, spread);
		float x = center[0] + Math.Cos(a) * r;
		float z = center[2] + Math.Sin(a) * r;
		float y = GetGame().SurfaceY(x, z);
		return Vector(x, y, z);
	}

	protected static void SetupItem(EntityAI e)
	{
		ItemBase ib = ItemBase.Cast(e);
		if (!ib) return;
		ib.SetHealth("", "", ib.GetMaxHealth());
		Magazine mag = Magazine.Cast(e);
		if (mag) mag.ServerSetAmmoMax();
	}

	protected static void AttachAttachments(EntityAI host, array<string> atts)
	{
		if (!atts) return;
		foreach (string cls : atts)
		{
			if (cls == "") continue;
			EntityAI a = host.GetInventory().CreateAttachment(cls);
			if (a) SetupItem(a);
		}
	}

	protected static void FillCargo(EntityAI host, array<string> cargo)
	{
		if (!cargo) return;
		foreach (string cls : cargo)
		{
			if (cls == "") continue;
			EntityAI c = EntityAI.Cast(host.GetInventory().CreateInInventory(cls));
			if (c) SetupItem(c);
		}
	}

	protected static void ScheduleCleanup(EntityAI e, int lifetimeSec)
	{
		if (lifetimeSec <= 0) return;
		GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(DeleteItem, lifetimeSec * 1000, false, e);
	}

	protected static void DeleteItem(EntityAI e)
	{
		if (e) GetGame().ObjectDelete(e);
	}
}
