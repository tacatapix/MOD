; NSIS installer for EconomiaApp - DayZ Economy Configuration Generator
; Produces: EconomiaApp-Setup.exe

!define APP_NAME       "Economia DayZ"
!define APP_ID         "EconomiaApp"
!define APP_VERSION    "1.0.0"
!define APP_PUBLISHER  "tacatapix"
!define APP_URL        "https://github.com/tacatapix/MOD"
!define APP_EXE_BAT    "EconomiaApp.bat"

Unicode true
SetCompressor /SOLID lzma

Name          "${APP_NAME}"
OutFile       "EconomiaApp-Setup.exe"
InstallDir    "$LOCALAPPDATA\Programs\${APP_ID}"
InstallDirRegKey HKCU "Software\${APP_ID}" "InstallPath"
RequestExecutionLevel user
ShowInstDetails show
ShowUninstDetails show

VIProductVersion "1.0.0.0"
VIAddVersionKey "ProductName"    "${APP_NAME}"
VIAddVersionKey "CompanyName"    "${APP_PUBLISHER}"
VIAddVersionKey "FileVersion"    "${APP_VERSION}"
VIAddVersionKey "ProductVersion" "${APP_VERSION}"
VIAddVersionKey "FileDescription" "${APP_NAME} - Gerador de configuracoes DayZ"
VIAddVersionKey "LegalCopyright"  "MIT License"

!include "MUI2.nsh"
!define MUI_ABORTWARNING
!define MUI_LANGDLL_ALLLANGUAGES

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE_BAT}"
!define MUI_FINISHPAGE_RUN_TEXT "Iniciar ${APP_NAME} agora"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\LEIAME.txt"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "Abrir LEIAME"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "PortugueseBR"
!insertmacro MUI_LANGUAGE "English"

Section "-Core" SEC_CORE
  SetOutPath "$INSTDIR"
  File /r "..\dist\EconomiaApp\*.*"

  WriteRegStr HKCU "Software\${APP_ID}" "InstallPath" "$INSTDIR"
  WriteRegStr HKCU "Software\${APP_ID}" "Version"     "${APP_VERSION}"

  ; Uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" \
    "DisplayName"     "${APP_NAME}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" \
    "DisplayVersion"  "${APP_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" \
    "Publisher"       "${APP_PUBLISHER}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" \
    "URLInfoAbout"    "${APP_URL}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" \
    "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" \
    "DisplayIcon"     "$INSTDIR\python\pythonw.exe,0"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" \
    "InstallLocation" "$INSTDIR"
SectionEnd

Section "Atalho no Menu Iniciar" SEC_STARTMENU
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" \
                 "$INSTDIR\python\pythonw.exe" \
                 "$\"$INSTDIR\app\src\gui.py$\"" \
                 "$INSTDIR\python\pythonw.exe" 0 \
                 SW_SHOWNORMAL "" "Gerador de configuracoes DayZ"
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\LEIAME.lnk" \
                 "$INSTDIR\LEIAME.txt"
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\Desinstalar.lnk" \
                 "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Atalho na Area de Trabalho" SEC_DESKTOP
  CreateShortCut "$DESKTOP\${APP_NAME}.lnk" \
                 "$INSTDIR\python\pythonw.exe" \
                 "$\"$INSTDIR\app\src\gui.py$\"" \
                 "$INSTDIR\python\pythonw.exe" 0 \
                 SW_SHOWNORMAL "" "Gerador de configuracoes DayZ"
SectionEnd

Section "Uninstall"
  ; Shortcuts
  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\LEIAME.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\Desinstalar.lnk"
  RMDir  "$SMPROGRAMS\${APP_NAME}"

  ; Install tree - remove everything we shipped
  RMDir /r "$INSTDIR\python"
  RMDir /r "$INSTDIR\app"
  Delete "$INSTDIR\EconomiaApp.bat"
  Delete "$INSTDIR\EconomiaApp.vbs"
  Delete "$INSTDIR\LEIAME.txt"
  Delete "$INSTDIR\Uninstall.exe"
  ; Leave Saida/ (user's generated output) intact; remove if empty
  RMDir  "$INSTDIR\Saida"
  RMDir  "$INSTDIR"

  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}"
  DeleteRegKey HKCU "Software\${APP_ID}"
SectionEnd
