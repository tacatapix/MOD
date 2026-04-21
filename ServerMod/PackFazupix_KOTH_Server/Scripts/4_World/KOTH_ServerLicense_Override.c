//----------------------------------------------------------------------------
//  Server-only override of KOTH_ServerLicense.
//
//  This PBO must be loaded via -servermod=@PackFazupix_KOTH_Server so that
//  ONLY the server sees this class. Clients receive only the main mod,
//  which carries the stub (IsAuthorized -> false). When the companion
//  main mod boots on the server, the engine picks this modded class as
//  the runtime definition and IsAuthorized() becomes true.
//
//  Do not copy, share, or publish the contents of this PBO alongside the
//  main mod. Treat it as a keyfile.
//----------------------------------------------------------------------------

modded class KOTH_ServerLicense
{
	override bool IsAuthorized()
	{
		return true;
	}

	override string GetLicenseId()
	{
		return "PKFZ-KOTH-2025-PRIVATE";
	}
}
