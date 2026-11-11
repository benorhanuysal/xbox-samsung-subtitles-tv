@echo off
rem Ortak yardimci: TV IP'sini sorar, scripts\tv_ip.txt dosyasinda hatirlar (git'e girmez).
set TVIP=
if exist "%~dp0tv_ip.txt" set /p TVIP=<"%~dp0tv_ip.txt"
if defined TVIP (
    echo Kayitli TV IP: %TVIP%   ^(degistirmek icin scripts\tv_ip.txt dosyasini sil^)
    exit /b 0
)
set /p TVIP=TV'nin IP adresi (TV: Ayarlar ^> Genel ^> Ag ^> Ag Durumu):
if not defined TVIP ( echo HATA: IP girilmedi & exit /b 1 )
>"%~dp0tv_ip.txt" echo %TVIP%
exit /b 0
