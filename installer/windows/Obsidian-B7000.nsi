; Obsidian-B7000 VST3 installer (NSIS). Windows has no AU format, so there's no plugin-type choice
; here — VST3 only, installed to the shared system VST3 folder.
;
; Build with (from repo root, after building ObsidianB7000_VST3):
;   makensis /DVERSION=0.1.0 /DARTEFACTS_DIR=build\ObsidianB7000_artefacts\Release\VST3 installer\windows\Obsidian-B7000.nsi
;
; ARTEFACTS_DIR should point at the directory CONTAINING Obsidian-B7000.vst3 (i.e. the VST3 release
; output folder), not Obsidian-B7000.vst3 itself.

!ifndef VERSION
  !define VERSION "0.0.0"
!endif
!ifndef ARTEFACTS_DIR
  !define ARTEFACTS_DIR "..\..\build\ObsidianB7000_artefacts\Release\VST3"
!endif

Name "Obsidian-B7000"
OutFile "Obsidian-B7000-Windows-v${VERSION}-Installer.exe"
InstallDir "$COMMONFILES64\VST3"
RequestExecutionLevel admin
SetCompressor /SOLID lzma

Page directory
Page instfiles
UninstPage uninstConfirm
UninstPage instfiles

Section "Obsidian-B7000 VST3 Plugin" SecVST3
    SetOutPath "$INSTDIR\Obsidian-B7000.vst3"
    File /r "${ARTEFACTS_DIR}\Obsidian-B7000.vst3\*.*"

    WriteUninstaller "$INSTDIR\Obsidian-B7000.vst3\Uninstall-Obsidian-B7000.exe"

    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Obsidian-B7000" \
        "DisplayName" "Obsidian-B7000 VST3"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Obsidian-B7000" \
        "UninstallString" "$INSTDIR\Obsidian-B7000.vst3\Uninstall-Obsidian-B7000.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Obsidian-B7000" \
        "DisplayVersion" "${VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Obsidian-B7000" \
        "Publisher" "Leigh Pierce"
SectionEnd

Section "Uninstall"
    RMDir /r "$INSTDIR\Obsidian-B7000.vst3"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Obsidian-B7000"
SectionEnd
