@echo off
rem LunaTranslator ag servisi (TCP 2333) icin yerel agdan gelen baglantiya izin verir.
rem Cift tikla -> "Evet" de. Yonetici iznini kendisi ister.
rem Allows inbound TCP 2333 (LunaTranslator network service) from the local subnet only.
net session >nul 2>&1
if errorlevel 1 (
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)
netsh advfirewall firewall delete rule name="xbox-samsung-subtitles-tv 2333" >nul 2>&1
netsh advfirewall firewall add rule name="xbox-samsung-subtitles-tv 2333" dir=in action=allow protocol=TCP localport=2333 remoteip=localsubnet profile=any
if errorlevel 1 (
    echo HATA: kural eklenemedi.
) else (
    echo TAMAM: 2333 portu yerel agdan gelen baglantilara acildi.
)
pause
