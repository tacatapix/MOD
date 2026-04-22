// -----------------------------------------------------------------------------
//  KOTH_Log - thin wrapper around DayZ Print() with mod prefix and levels.
// -----------------------------------------------------------------------------

class KOTH_Log
{
	static const int LEVEL_ERROR = 0;
	static const int LEVEL_WARN  = 1;
	static const int LEVEL_INFO  = 2;
	static const int LEVEL_DEBUG = 3;

	//! Verbosity threshold - messages above this value are dropped.
	//! Overwritten at runtime from settings.json (LogLevel).
	static int m_Level = LEVEL_INFO;

	static void SetLevel(int lvl) { m_Level = lvl; }

	static void Error(string msg) { Write(LEVEL_ERROR, "ERROR", msg); }
	static void Warn (string msg) { Write(LEVEL_WARN , "WARN" , msg); }
	static void Info (string msg) { Write(LEVEL_INFO , "INFO" , msg); }
	static void Debug(string msg) { Write(LEVEL_DEBUG, "DEBUG", msg); }

	protected static void Write(int lvl, string tag, string msg)
	{
		if (lvl > m_Level) return;
		Print("[KOTH][" + tag + "] " + msg);
	}
}
