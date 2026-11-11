@echo off
chcp 65001 >nul
title TV uygulamasini paketle ve TV'ye yukle
set TZ=C:\tizen-studio
set TIZEN=%TZ%\tools\ide\bin\tizen.bat
set SDB=%TZ%\tools\sdb.exe
set PROJE=%~dp0..\tv-app
set PROFIL=AltyaziTV
set APPID=AltyzTV001.AltyaziTV
rem Turkce yerel ayarda Tizen araclari "I" harfi yuzunden cokuyor (profiles.xml NullPointerException).
set JAVA_TOOL_OPTIONS=-Duser.language=en -Duser.country=US

if not exist "%TIZEN%" ( echo HATA: tizen CLI bulunamadi: %TIZEN% & pause & exit /b 1 )
call "%~dp0_tv_ip.bat" || ( pause & exit /b 1 )

echo [1/4] TV'ye baglaniliyor (%TVIP%)...
"%SDB%" connect %TVIP%
"%SDB%" devices

echo.
echo [2/4] Uygulama derleniyor...
pushd "%PROJE%"
if exist .buildResult rmdir /s /q .buildResult
call "%TIZEN%" build-web -- "%PROJE%"
if errorlevel 1 ( echo HATA: derleme basarisiz & popd & pause & exit /b 1 )

echo.
echo [3/4] Paketleniyor (sertifika profili: %PROFIL%)...
call "%TIZEN%" package -t wgt -s %PROFIL% -- "%PROJE%\.buildResult"
if errorlevel 1 ( echo HATA: paketleme basarisiz. "%PROFIL%" sertifika profili var mi? & popd & pause & exit /b 1 )
rem Dosya adindaki bosluk "tizen install"i bozuyor
for %%W in ("%PROJE%\.buildResult\*.wgt") do if not "%%~nxW"=="AltyaziTV.wgt" ren "%%W" AltyaziTV.wgt

echo.
echo [4/4] TV'ye yukleniyor ve baslatiliyor...
call "%TIZEN%" install -n AltyaziTV.wgt -s %TVIP%:26101 -- "%PROJE%\.buildResult"
call "%TIZEN%" run -p %APPID% -s %TVIP%:26101
popd
pause
