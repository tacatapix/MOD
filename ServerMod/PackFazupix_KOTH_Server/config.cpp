class CfgPatches
{
	class PackFazupix_KOTH_Server
	{
		units[] = {};
		weapons[] = {};
		requiredVersion = 0.1;
		requiredAddons[] =
		{
			"DZ_Data",
			"DZ_Scripts",
			"PackFazupix_KOTH"
		};
	};
};

class CfgMods
{
	class PackFazupix_KOTH_Server
	{
		type      = "mod";
		dir       = "PackFazupix_KOTH_Server";
		name      = "PackFazupix KOTH (Server)";
		author    = "PackFazupix";
		credits   = "PackFazupix";
		picture   = "";
		logo      = "";
		overview  = "Server-only license PBO for PackFazupix KOTH.";
		inputs    = "";
		dependencies[] = {"Game","World","Mission"};

		class defs
		{
			class worldScriptModule
			{
				value   = "";
				files[] = {"PackFazupix_KOTH_Server/Scripts/4_World"};
			};
		};
	};
};
