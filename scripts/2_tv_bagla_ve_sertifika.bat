@echo off
chcp 65001 >nul
title TV'ye baglan ve Samsung sertifikasi olustur
set TZ=C:\tizen-studio
set SDB=%TZ%\tools\sdb.exe
set CM=%TZ%\tools\certificate-manager
if not exist "%SDB%" ( echo HATA: Tizen SDK bulunamadi: %TZ%  ^(README: Kurulum 2^) & pause & exit /b 1 )

echo Bu PC'nin IP adres(ler)i - TV'de Developer Mode ^> Host PC IP olarak bunu gir:
powershell -NoProfile -Command "Get-NetIPAddress -AddressFamily IPv4 | ? { $_.PrefixOrigin -eq 'Dhcp' -or $_.PrefixOrigin -eq 'Manual' } | ? { $_.IPAddress -notlike '169.254*' } | %% { '   ' + $_.IPAddress + '  (' + $_.InterfaceAlias + ')' }"
echo.
call "%~dp0_tv_ip.bat" || exit /b 1
"%SDB%" connect %TVIP%
"%SDB%" devices
echo.
echo Listede TV gorunuyorsa sertifika yoneticisi aciliyor...
echo  + ^> Samsung ^> TV ^> profil adi: AltyaziTV
echo  Author: yeni olustur ^> sifre belirle ^> Samsung hesabinla giris yap (tarayicida)
echo  Distributor: Privilege "Public" ^> DUID listesinde TV otomatik gelir
echo.
rem ONEMLI: Turkce Windows'ta Java "WINDOWS" kelimesini yanlis kucultuyor (I -> ı), arac sdb'yi
rem bulamiyor ve Samsung secenegi sessizce kapaniyor. Bu yuzden Ingilizce yerel ayarla aciliyor.
rem certificate-manager.exe de sessizce kapanabildigi icin dogrudan Java ile baslatiliyor.
pushd "%CM%"
for %%J in (plugins\org.eclipse.equinox.launcher_*.jar) do set LAUNCHER=%%J
start "" "%TZ%\jdk\bin\javaw.exe" -Duser.language=en -Duser.country=US -Dfile.encoding=UTF-8 -jar "%LAUNCHER%"
popd
pause
