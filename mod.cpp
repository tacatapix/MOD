#define MOD_NAME "PackFazupix_KOTH"

class CfgMods
{
	class PackFazupix_KOTH
	{
		dir           = "PackFazupix_KOTH";
		picture       = "";
		action        = "";
		hideName      = 0;
		hidePicture   = 0;
		name          = "PackFazupix KOTH";
		credits       = "PackFazupix";
		author        = "PackFazupix";
		authorID      = "0";
		version       = "1.0.0";
		extra         = 0;
		type          = "mod";

		dependencies[] = {"Game","World","Mission"};

		class defs
		{
			class gameScriptModule
			{
				value     = "";
				files[]   = {"PackFazupix_KOTH/Scripts/3_Game"};
			};
			class worldScriptModule
			{
				value     = "";
				files[]   = {"PackFazupix_KOTH/Scripts/4_World"};
			};
			class missionScriptModule
			{
				value     = "";
				files[]   = {"PackFazupix_KOTH/Scripts/5_Mission"};
			};
		};
	};
};
