// -----------------------------------------------------------------------------
//  KOTH_Messages - configurable broadcast strings loaded from messages.json
//
//  Placeholders supported (all optional):
//    {zone}     - zone display name
//    {seconds}  - seconds remaining
//    {minutes}  - minutes remaining (rounded)
//    {player}   - player name (capture events)
//    {tier}     - tier label
//    {count}    - number of players inside the capture radius
// -----------------------------------------------------------------------------

class KOTH_Messages
{
	string PreStartAnnounce     = "[KOTH] O evento {zone} comeca em {minutes} minutos!";
	string PreStartTick         = "[KOTH] {zone} em {seconds}s...";
	string Started              = "[KOTH] {zone} ESTA ATIVO! Corre pra la!";
	string CaptureStarted       = "[KOTH] {player} comecou a capturar {zone} ({count} jogadores na zona)";
	string CaptureContested     = "[KOTH] {zone} esta sendo disputado!";
	string Captured             = "[KOTH] {player} capturou {zone} e ganhou {tier}!";
	string Ended                = "[KOTH] {zone} terminou. Proximo evento em breve.";

	//! In-game HUD label next to the capture bar.
	string HudCaptureLabel      = "Capturando {zone}";
	string HudContestedLabel    = "Contestado - {count} na zona";
	string HudPlayersInZone     = "Jogadores na zona: {count}";
}
