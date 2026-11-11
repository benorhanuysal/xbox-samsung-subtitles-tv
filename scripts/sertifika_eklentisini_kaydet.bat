@echo off
chcp 65001 >nul
rem SORUN: Paket yoneticisi "cert-add-on / Certificate-Manager kurulamadi" deyip Samsung eklentisini
rem Sertifika Yoneticisi'ne kaydetmiyor; "+" > sadece "Tizen" gorunuyor ya da Samsung secenegi yok.
rem COZUM: plugins\org.tizen.common.cert_*.jar dosyasini bundles.info'ya ekler (once yedek alir).
set CM=C:\tizen-studio\tools\certificate-manager
powershell -NoProfile -Command ^
  "$cm='%CM%'; $b=Join-Path $cm 'configuration\org.eclipse.equinox.simpleconfigurator\bundles.info';" ^
  "if(-not (Test-Path $b)){ 'HATA: bundles.info yok - Certificate-Manager kurulu mu?'; exit 1 };" ^
  "$jar=Get-ChildItem (Join-Path $cm 'plugins') -Filter 'org.tizen.common.cert_*.jar' | Sort-Object Name | Select-Object -Last 1;" ^
  "if(-not $jar){ 'HATA: org.tizen.common.cert_*.jar yok - cert-add-on paketi kurulu mu?'; exit 1 };" ^
  "if(Select-String -Path $b -SimpleMatch 'org.tizen.common.cert,' -Quiet){ 'Zaten kayitli, bir sey yapilmadi.'; exit 0 };" ^
  "$v=$jar.BaseName -replace '^org\.tizen\.common\.cert_','';" ^
  "Copy-Item $b ($b+'.yedek') -Force;" ^
  "$t=[IO.File]::ReadAllText($b); if(-not $t.EndsWith([string][char]10)){ $t+=[char]10 };" ^
  "[IO.File]::WriteAllText($b, $t+('org.tizen.common.cert,'+$v+',plugins/'+$jar.Name+',4,false')+[char]10, (New-Object Text.UTF8Encoding $false));" ^
  "'TAMAM: Samsung sertifika eklentisi kaydedildi ('+$v+').'"
pause
