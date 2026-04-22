//----------------------------------------------------------------------------
//  KOTH_ServerLicense - client+server stub.
//
//  The main mod (this PBO) ships the stub below to every client. The stub
//  always reports UNAUTHORIZED so the mod refuses to run without the
//  companion server-only PBO.
//
//  The companion mod (@PackFazupix_KOTH_Server, loaded via -servermod=)
//  contains a `modded class KOTH_ServerLicense` that overrides
//  IsAuthorized() and GetLicenseId() to return valid values. Because a
//  server-only mod is loaded AFTER regular mods on the server side, the
//  `modded` override takes precedence and the KOTH manager starts.
//
//  On a client, only this stub is loaded -> IsAuthorized() == false ->
//  the Manager never runs (server-side code is gated on IsServer() too).
//
//  If someone copies this PBO to their own server without the companion
//  server mod, the stub runs, IsAuthorized() returns false, and the
//  Manager refuses to start. The attacker would have to patch/re-sign
//  the PBO to bypass it, which changes the signature.
//----------------------------------------------------------------------------

class KOTH_ServerLicense
{
    static ref KOTH_ServerLicense s_Instance;

    static KOTH_ServerLicense Get()
    {
        if (!s_Instance) s_Instance = new KOTH_ServerLicense();
        return s_Instance;
    }

    // Returns true only when the companion server mod is loaded.
    bool IsAuthorized()
    {
        return false;
    }

    // Opaque license identifier. The server mod returns a magic string
    // that gets logged at boot so you can confirm the correct license
    // is active.
    string GetLicenseId()
    {
        return "";
    }

    // Human-readable diagnostic. Override only for nicer logs.
    string GetDiagnostic()
    {
        if (IsAuthorized())
            return "licensed (" + GetLicenseId() + ")";
        return "UNLICENSED - @PackFazupix_KOTH_Server not loaded in -servermod=";
    }
}
