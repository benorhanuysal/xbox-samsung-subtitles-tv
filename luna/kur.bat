@echo off
chcp 65001 >nul
title LunaTranslator eklentilerini kur
rem mypost.py (altyazi filtresi) ve selfbuild.py (Gemini+Google cevirici) dosyalarini
rem LunaTranslator'in userconfig klasorune kopyalar. Ayarlar icin README > "LunaTranslator ayarlari".

set LUNA=
set /p LUNA=LunaTranslator klasoru (LunaTranslator.exe'nin oldugu yer):
if not defined LUNA ( echo HATA: klasor girilmedi & pause & exit /b 1 )
set LUNA=%LUNA:"=%
if not exist "%LUNA%\LunaTranslator.exe" ( echo HATA: "%LUNA%\LunaTranslator.exe" bulunamadi & pause & exit /b 1 )
tasklist /fi "imagename eq LunaTranslator.exe" | find /i "LunaTranslator.exe" >nul && (
    echo HATA: LunaTranslator acik. Tepsi simgesine sag tikla ^> Cikis, sonra tekrar calistir.
    pause & exit /b 1
)
if not exist "%LUNA%\userconfig" mkdir "%LUNA%\userconfig"
for %%F in (mypost.py selfbuild.py) do (
    if exist "%LUNA%\userconfig\%%F" copy /y "%LUNA%\userconfig\%%F" "%LUNA%\userconfig\%%F.yedek" >nul
    copy /y "%~dp0%%F" "%LUNA%\userconfig\%%F" >nul && echo kopyalandi: %%F
)
echo.
echo TAMAM. Simdi LunaTranslator'i acip README'deki ayarlari yap.
pause
