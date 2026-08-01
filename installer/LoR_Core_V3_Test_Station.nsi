Unicode True
SetCompressor /SOLID lzma

!include "MUI2.nsh"
!include "x64.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

!define APP_NAME "LoR Core V3 Test Station"
!define APP_VERSION "1.14.1"
!define APP_PUBLISHER "Lord of Robots"
!define APP_EXE "LoR Core V3 Test Station.exe"
!define APP_ID "{7C69FC40-ED8E-4A91-8B38-84FA493FEE07}"
!define APP_SOURCE "${__FILEDIR__}\output\app\LoR Core V3 Test Station"

Name "${APP_NAME}"
OutFile "${__FILEDIR__}\output\LoR_Core_V3_Test_Station_Setup_${APP_VERSION}.exe"
InstallDir "$PROGRAMFILES64\Lord of Robots\${APP_NAME}"
InstallDirRegKey HKLM "Software\Lord of Robots\${APP_NAME}" "InstallDir"
RequestExecutionLevel admin
BrandingText "Lord of Robots"
Icon "${__FILEDIR__}\..\production_test\assets\lor-test-station.ico"
UninstallIcon "${__FILEDIR__}\..\production_test\assets\lor-test-station.ico"

VIProductVersion "1.14.1.0"
VIAddVersionKey /LANG=1033 "ProductName" "${APP_NAME}"
VIAddVersionKey /LANG=1033 "CompanyName" "${APP_PUBLISHER}"
VIAddVersionKey /LANG=1033 "FileDescription" "${APP_NAME} Installer"
VIAddVersionKey /LANG=1033 "FileVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1033 "ProductVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1033 "LegalCopyright" "Copyright ${APP_PUBLISHER}"

!define MUI_ABORTWARNING
!define MUI_ICON "${__FILEDIR__}\..\production_test\assets\lor-test-station.ico"
!define MUI_UNICON "${__FILEDIR__}\..\production_test\assets\lor-test-station.ico"
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${APP_NAME}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "${APP_NAME} requires 64-bit Windows."
    Abort
  ${EndIf}
  SetRegView 64

  ; Compatibility with updater arguments used by app version 1.14.0.
  ${GetParameters} $R0
  ClearErrors
  ${GetOptions} $R0 "/VERYSILENT" $R1
  ${IfNot} ${Errors}
    SetSilent silent
  ${EndIf}
FunctionEnd

Section "Install"
  SetShellVarContext all
  SetRegView 64

  ; Close the station before replacing its frozen runtime during an update.
  nsExec::ExecToLog '"$SYSDIR\taskkill.exe" /IM "${APP_EXE}" /F'

  ; Remove the prior runtime completely so upgrades cannot retain stale files.
  RMDir /r "$INSTDIR"
  SetOutPath "$INSTDIR"
  File /r "${APP_SOURCE}\*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; With all-users shell context, $APPDATA resolves to ProgramData.
  CreateDirectory "$APPDATA\Lord of Robots\${APP_NAME}\results"
  CreateDirectory "$APPDATA\Lord of Robots\${APP_NAME}\build"
  CreateDirectory "$APPDATA\Lord of Robots\${APP_NAME}\firmware"
  CreateDirectory "$APPDATA\Lord of Robots\${APP_NAME}\updates"
  nsExec::ExecToLog '"$SYSDIR\icacls.exe" "$APPDATA\Lord of Robots\${APP_NAME}" /grant *S-1-5-32-545:(OI)(CI)M /T /C'

  CreateDirectory "$SMPROGRAMS\Lord of Robots"
  CreateShortcut "$SMPROGRAMS\Lord of Robots\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0

  WriteRegStr HKLM "Software\Lord of Robots\${APP_NAME}" "InstallDir" "$INSTDIR"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}_is1"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "Publisher" "${APP_PUBLISHER}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}" "NoRepair" 1

  IfSilent 0 install_done
  Exec '"$INSTDIR\${APP_EXE}"'
install_done:
SectionEnd

Section "Uninstall"
  SetShellVarContext all
  SetRegView 64
  nsExec::ExecToLog '"$SYSDIR\taskkill.exe" /IM "${APP_EXE}" /F'
  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\Lord of Robots\${APP_NAME}.lnk"
  RMDir "$SMPROGRAMS\Lord of Robots"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_ID}_is1"
  DeleteRegKey HKLM "Software\Lord of Robots\${APP_NAME}"
  RMDir /r "$INSTDIR"
  ; ProgramData is intentionally preserved as the manufacturing audit record.
SectionEnd
