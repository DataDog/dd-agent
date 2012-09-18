;--------------------------------
;Includes

  !include "MUI2.nsh"
  !include "nsDialogs.nsh"
  !include "LogicLib.nsh"
  !include "StrRep.nsh"
  !include "ReplaceInFile.nsh"

;--------------------------------
;General
  ;Name and file
  Name "Datadog Agent"
  OutFile "DDAgentInstall.exe"

  ;Default installation folder
  InstallDir "$PROGRAMFILES\Datadog Agent"

  ;Get installation folder from registry if available
  InstallDirRegKey HKCU "Software\Datadog Agent" ""

  ;Request application privileges for Windows Vista
  RequestExecutionLevel admin

  ;Icon "agent_install.ico"
  Caption "Datadog Agent Setup"
  VIProductVersion "1.3.1.0"
  VIAddVersionKey ProductName "Datadog Agent"
  VIAddVersionKey Comments "Captures system and application metrics and sends them to your Datadog account."
  VIAddVersionKey CompanyName "Datadog, Inc."
  VIAddVersionKey LegalCopyright Datadoghq.com
  VIAddVersionKey FileDescription "Datadog Agent"
  VIAddVersionKey FileVersion ${Version}
  VIAddVersionKey ProductVersion ${Version}
  VIAddVersionKey InternalName "Datadog Agent"
  VIAddVersionKey LegalTrademarks "Copyright 2012 Datadog, Inc. 2012"

;--------------------------------
;Interface Settings

  !define MUI_ABORTWARNING

;--------------------------------
;Uninstall Pages

  !insertmacro MUI_UNPAGE_CONFIRM
  !insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
; License Page

  !insertmacro MUI_PAGE_LICENSE "install_files\license.txt"

;--------------------------------
; Components Page

  !insertmacro MUI_PAGE_COMPONENTS

;--------------------------------
; Directory Page

  !insertmacro MUI_PAGE_DIRECTORY

;-------------------------------
; Install Files Page

  !insertmacro MUI_PAGE_INSTFILES

;--------------------------------
; API Info Page

  Var Dialog
  Var Label
  Var Text
  var Checkbox

  Page custom apiInfo infoSave

  Function apiInfo
    SetShellVarContext all
    StrCpy $0 $APPDATA
    SetShellVarContext current

    nsDialogs::Create 1018
    Pop $Dialog

    ${If} $Dialog == error
      Abort
    ${EndIf}

    ${NSD_CreateLabel} 0 0 100% 12u "Please enter your Datadog API Key:"
    Pop $Label

    ${NSD_CreateText} 0 13u 100% 14u ""
    Pop $Text

    ${NSD_CreateCheckBox} 0 40u 100% 12u "  Install the Agent as a service."
    Pop $Checkbox

    ${NSD_SetState} $Checkbox ${BST_CHECKED}

    nsDialogs::Show

  FunctionEnd

  Function infoSave

    ${NSD_GetText} $Text $1
    !insertmacro _ReplaceInFile "$0\Datadog Agent\datadog.conf" "APIKEYHERE" "api_key: $1"

    ${NSD_GetState} $Checkbox $1
    ${IF} $1 == ${BST_CHECKED}
      ; Install and start the agent
      Exec "$INSTDIR\ddagent.exe --startup auto install"
      Exec "$INSTDIR\ddagent.exe start"
    ${ENDIF}

  FunctionEnd

;--------------------------------
; Finish Page

  !define MUI_FINISHPAGE_TEXT "If you chose to install the Agent as a service, it should be currently running in the background and submitting metrics to Datadog.$\n$\nOtherwise, you will have to setup the Agent services manually by navigating to $INSTDIR in the console and installing the necessary service (ddagent).$\n$\nAll the Datadog services can be configured (e.g., to automatically start on boot) with 'Services Properties' at $WINDIR\system32\services.msc."
  !insertmacro MUI_PAGE_FINISH


;--------------------------------
;Languages
 
  !insertmacro MUI_LANGUAGE "English"

;--------------------------------
;Installer Sections

Section "Datadog Agent" SecDummy
  ;Config will go in App Data
  SetShellVarContext all
  StrCpy $0 $APPDATA
  SetShellVarContext current

  SetOutPath "$INSTDIR"

  ; Files to install
  File "install_files\license.txt"
  File /oname=ddagent.exe "install_files\agent.exe"
  FILE "install_files\ca-certificates.crt"

  ; Config does in App Data
  SetOutPath "$0\Datadog Agent"
  File /oname=datadog.conf "install_files\datadog_win32.conf"

  ;Store installation folder
  WriteRegStr HKCU "Software\Datadog Agent" "" $INSTDIR
  
  ;Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Open the Readme file
  ExecShell "$INSTDIR\ddagent.exe" "install"

SectionEnd

;--------------------------------
;Descriptions

  ;Language strings
  LangString DESC_SecDummy ${LANG_ENGLISH} "Installs the Agent so that you can send metrics to Datadog."

  ;Assign language strings to sections
  !insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecDummy} $(DESC_SecDummy)
  !insertmacro MUI_FUNCTION_DESCRIPTION_END

;--------------------------------
;Uninstaller Section

Section "Uninstall"
  SetShellVarContext all
  StrCpy $0 $APPDATA
  SetShellVarContext current

  Delete "$INSTDIR\ddagent.exe"
  Delete "$0\Datadog Agent\datadog.conf"
  Delete "$INSTDIR\ca-certificates.crt"
  Delete "$INSTDIR\Uninstall.exe"

  RMDir "$INSTDIR"

  DeleteRegKey /ifempty HKCU "Software\Datadog Agent"

SectionEnd