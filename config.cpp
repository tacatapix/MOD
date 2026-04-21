class CfgPatches
{
	class PackFazupix_KOTH
	{
		units[] = {};
		weapons[] = {};
		requiredVersion = 0.1;
		requiredAddons[] =
		{
			"DZ_Data",
			"DZ_Scripts",
			"CF_Scripts"
		};
	};
};

class CfgMods
{
	class PackFazupix_KOTH
	{
		type      = "mod";
		dir       = "PackFazupix_KOTH";
		name      = "PackFazupix KOTH";
		author    = "PackFazupix";
		credits   = "PackFazupix";
		picture   = "";
		logo      = "";
		overview  = "King of the Hill event system for DayZ Chernarus.";
		inputs    = "";
		dependencies[] = {"Game","World","Mission"};

		class defs
		{
			class engineScriptModule
			{
				files[] = {};
			};
			class gameScriptModule
			{
				value   = "";
				files[] = {"PackFazupix_KOTH/Scripts/3_Game"};
			};
			class worldScriptModule
			{
				value   = "";
				files[] = {"PackFazupix_KOTH/Scripts/4_World"};
			};
			class missionScriptModule
			{
				value   = "";
				files[] = {"PackFazupix_KOTH/Scripts/5_Mission"};
			};
		};
	};
};
