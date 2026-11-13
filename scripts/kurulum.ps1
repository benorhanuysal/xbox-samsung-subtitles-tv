# xbox-samsung-subtitles-tv - tek tik kurulum
# Calistirma: depo kokundeki KUR.bat (cift tikla). Her adim yapilmissa atlanir; tekrar calistirmak guvenli.
# Kullanicinin elle yapacaklari: TV'de gelistirici modu, Samsung hesabiyla giris, Windows onay pencereleri.
#
#   -Adimlar  : yalnizca secilen adimlari calistir (or. -Adimlar luna,tv)
#               onkosul, tizen, eklenti, luna, guvenlik, tv, sertifika, yukle
#   -LunaYolu : LunaTranslator klasoru (LunaTranslator.exe'nin oldugu yer); verilmezse sorulur
param(
    [string[]]$Adimlar = @('onkosul', 'tizen', 'eklenti', 'luna', 'guvenlik', 'tv', 'sertifika', 'yukle'),
    [string]$LunaYolu
)
$ErrorActionPreference = 'Stop'
# "powershell -File ... -Adimlar luna,tv" virgullu listeyi tek metin olarak verir: bol
$Adimlar = @($Adimlar | ForEach-Object { $_ -split '[,\s]+' } | Where-Object { $_ } | ForEach-Object { $_.Trim().ToLowerInvariant() })
$ProgressPreference = 'SilentlyContinue'   # Invoke-WebRequest ilerleme cubugu PS 5.1'de indirmeyi cok yavaslatiyor
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Depo     = Split-Path -Parent $PSScriptRoot
$TZ       = 'C:\tizen-studio'
$TIZEN    = "$TZ\tools\ide\bin\tizen.bat"
$SDB      = "$TZ\tools\sdb.exe"
$CM       = "$TZ\tools\certificate-manager"
$PROFIL   = 'AltyaziTV'
$APPID    = 'AltyzTV001.AltyaziTV'
$TIZEN_URL  = 'https://download.tizen.org/sdk/Installer/tizen-sdk_10.0/web-cli_Tizen_SDK_10.0_windows-64.exe'
$LUNA_API   = 'https://api.github.com/repos/HIllya51/LunaTranslator/releases/latest'
# GTA V altyazi seridi (1920x1080'de 455,878 999x168); ekran cozunurlugune gore olceklenir.
# Daha genis tutulursa sag alttaki tus ipuclari (Respawn, Passive Mode) ve sol ustteki yardim kutusu karisir.
$BOLGE_ORAN = @(0.237, 0.813, 0.520, 0.156)
$GEMINI_PROMPT = 'You translate English video game subtitles from Grand Theft Auto into natural, casual Turkish. Output only the Turkish translation, nothing else. Keep it short like a subtitle. Never translate character names, place names, vehicle, weapon or brand names. Keep street slang and swearing in a natural Turkish equivalent. If the input is not a sentence (HUD text, a name, a number), output it unchanged.'
# Turkce Windows'ta Java "WINDOWS" kelimesini "wındows" yapiyor; Tizen araclari bu yuzden cokuyor.
$env:JAVA_TOOL_OPTIONS = '-Duser.language=en -Duser.country=US'

function Baslik($t) { Write-Host ''; Write-Host "==== $t ====" -ForegroundColor Cyan }
function Bilgi($t)  { Write-Host "  $t" }
function Tamam($t)  { Write-Host "  [OK] $t" -ForegroundColor Green }
function Uyari($t)  { Write-Host "  [!] $t" -ForegroundColor Yellow }
function Dur($t)    { Write-Host "  [HATA] $t" -ForegroundColor Red; Read-Host '  Cikmak icin Enter'; exit 1 }
function Adim($ad)  { $Adimlar -contains $ad }
# Windows PowerShell 5.1'de yerel programin hata akisina yazdigi her satir ($ErrorActionPreference='Stop' altinda)
# betigi durdurur: Java'nin "Picked up JAVA_TOOL_OPTIONS" bilgisi, sdb'nin "baglanamadi" mesaji (tekrar dene
# dongusune hic gelinmiyordu). Cikti cmd icinde birlestirilip metin olarak doner.
function Yerel([string]$komut) { & cmd /c "$komut 2>&1" | Out-String }

function JsonOku($yol) {
    if (Test-Path $yol) { return ([IO.File]::ReadAllText($yol, [Text.Encoding]::UTF8) | ConvertFrom-Json) }
    return (New-Object PSObject)
}
function JsonYaz($obj, $yol) {
    # Luna json.load(utf-8) BOM'u kabul etmiyor: BOM'suz yaz
    if (Test-Path $yol) { Copy-Item $yol "$yol.kurulum_yedek" -Force }
    [IO.File]::WriteAllText($yol, ($obj | ConvertTo-Json -Depth 100), (New-Object Text.UTF8Encoding $false))
}
function Ayarla($obj, $ad, $deger) {
    if ($obj.PSObject.Properties[$ad]) { $obj.$ad = $deger } else { $obj | Add-Member -NotePropertyName $ad -NotePropertyValue $deger }
}
function AltNesne($obj, $ad) {
    if (-not $obj.PSObject.Properties[$ad] -or $null -eq $obj.$ad) { Ayarla $obj $ad (New-Object PSObject) }
    return $obj.$ad
}
function TvIp {
    $dosya = Join-Path $PSScriptRoot 'tv_ip.txt'
    if (Test-Path $dosya) { $ip = (Get-Content $dosya -TotalCount 1).Trim(); if ($ip) { return $ip } }
    $ip = (Read-Host "  TV'nin IP adresi (TV: Ayarlar > Genel > Ag > Ag Durumu)").Trim()
    if (-not $ip) { Dur 'IP girilmedi.' }
    Set-Content $dosya $ip -Encoding ASCII
    return $ip
}
function PcIpleri {
    Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.PrefixOrigin -in 'Dhcp', 'Manual' -and $_.IPAddress -notlike '169.254*' } |
        ForEach-Object { "$($_.IPAddress)  ($($_.InterfaceAlias))" }
}

Write-Host 'xbox-samsung-subtitles-tv kurulumu' -ForegroundColor Cyan
Write-Host "Depo: $Depo"

# ---------------------------------------------------------------- 1. On kosullar
$ocrMotoru = 'SnippingTool'
if (Adim 'onkosul') {
    Baslik '1/8 On kosullar'
    $surum = [Environment]::OSVersion.Version
    if ($surum.Build -ge 22000) { Tamam "Windows 11 (build $($surum.Build))" }
    else { Uyari "Windows 11 degil (build $($surum.Build)): hizli OCR yok, Google Lens kullanilacak (daha yavas)."; $ocrMotoru = 'googlelens' }
    if ($ocrMotoru -eq 'SnippingTool' -and -not (Get-AppxPackage -Name 'Microsoft.ScreenSketch' -ErrorAction SilentlyContinue)) {
        Uyari "Ekran Alintisi Araci (Snipping Tool) yuklu degil: Microsoft Store'dan yukleyin ya da Google Lens kullanilacak."
        $ocrMotoru = 'googlelens'
    }
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Bilgi 'git yok (zorunlu degil).' }
    Tamam "OCR motoru: $ocrMotoru"
}

# ---------------------------------------------------------------- 2. Tizen SDK
if (Adim 'tizen') {
    Baslik '2/8 Tizen SDK'
    if (Test-Path $TIZEN) { Tamam "Kurulu: $TZ" }
    else {
        $kurulum = Join-Path $env:TEMP 'web-cli_Tizen_SDK_10.0_windows-64.exe'
        $beklenen = [int64](Invoke-WebRequest $TIZEN_URL -Method Head -UseBasicParsing).Headers['Content-Length']
        if (-not (Test-Path $kurulum) -or (Get-Item $kurulum).Length -ne $beklenen) {
            Bilgi ("Indiriliyor ({0:N0} MB), birkac dakika surebilir..." -f ($beklenen / 1MB))
            Invoke-WebRequest $TIZEN_URL -OutFile $kurulum -UseBasicParsing
        }
        if ((Get-Item $kurulum).Length -ne $beklenen) { Dur 'Indirme eksik kaldi (yarim inen dosya "gecerli bir Win32 uygulamasi degil" hatasi verir). Tekrar deneyin.' }
        Bilgi "Kuruluyor: $TZ"
        $p = Start-Process $kurulum -ArgumentList '--accept-license', $TZ -Wait -PassThru
        if (-not (Test-Path $TIZEN)) { Dur "Tizen kurulamadi (cikis kodu $($p.ExitCode))." }
        Tamam 'Tizen SDK kuruldu'
    }
}

# ---------------------------------------------------------------- 3. Samsung sertifika eklentileri
if (Adim 'eklenti') {
    Baslik '3/8 Samsung sertifika eklentileri'
    $certJar = Get-ChildItem "$CM\plugins" -Filter 'org.tizen.common.cert_*.jar' -ErrorAction SilentlyContinue | Select-Object -Last 1
    if (-not ((Test-Path "$CM\plugins") -and $certJar)) {
        # package-manager-cli.exe adindan dolayi yonetici istiyor; jar dogrudan calistirilir.
        # Kendi JDK'siyla calisirsa WebCLI guncellemesi o JDK'yi yarida birakip bozuyor: kopyasini kullan.
        $jdk = Join-Path $env:TEMP 'tizen-jdk-kopya'
        if (-not (Test-Path "$jdk\bin\java.exe")) { Bilgi 'JDK kopyalaniyor...'; Copy-Item "$TZ\jdk" $jdk -Recurse -Force }
        Push-Location "$TZ\package-manager"
        foreach ($paket in 'cert-add-on', 'Certificate-Manager') {
            Bilgi "Kuruluyor: $paket"
            Yerel "`"$jdk\bin\java.exe`" -jar PackageManagerV2-cli.jar install --accept-license $paket" | Out-Null
            # "Installation has been failed" deyip dosyalari yine de acabiliyor; asagida kontrol ediliyor
        }
        Pop-Location
        $certJar = Get-ChildItem "$CM\plugins" -Filter 'org.tizen.common.cert_*.jar' -ErrorAction SilentlyContinue | Select-Object -Last 1
    }
    if (-not (Test-Path "$CM\plugins") -or -not $certJar) { Dur 'Sertifika Yoneticisi / Samsung eklentisi kurulamadi. C:\tizen-studio\package-manager\package-manager.exe ile elle kurun.' }
    $bi = "$CM\configuration\org.eclipse.equinox.simpleconfigurator\bundles.info"
    if (Select-String -Path $bi -SimpleMatch 'org.tizen.common.cert,' -Quiet) { Tamam 'Samsung eklentisi kayitli' }
    else {
        $v = $certJar.BaseName -replace '^org\.tizen\.common\.cert_', ''
        Copy-Item $bi "$bi.yedek" -Force
        $t = [IO.File]::ReadAllText($bi); if (-not $t.EndsWith("`n")) { $t += "`n" }
        [IO.File]::WriteAllText($bi, $t + "org.tizen.common.cert,$v,plugins/$($certJar.Name),4,false`n", (New-Object Text.UTF8Encoding $false))
        Tamam "Samsung eklentisi kaydedildi ($v)"
    }
}

# ---------------------------------------------------------------- 4. LunaTranslator
if (Adim 'luna') {
    Baslik '4/8 LunaTranslator'
    if (-not $LunaYolu) {
        $varsayilan = Join-Path $env:USERPROFILE 'LunaTranslator'
        $LunaYolu = (Read-Host "  LunaTranslator klasoru (bos birakirsan indirilip $varsayilan altina kurulur)").Trim().Trim('"')
        if (-not $LunaYolu) { $LunaYolu = $varsayilan }
    }
    if (-not (Test-Path "$LunaYolu\LunaTranslator.exe")) {
        $rel = Invoke-RestMethod $LUNA_API -Headers @{ 'User-Agent' = 'xbox-samsung-subtitles-tv' }
        $varlik = $rel.assets | Where-Object { $_.name -eq 'LunaTranslator_x64.zip' } | Select-Object -First 1
        if (-not $varlik) { Dur 'LunaTranslator_x64.zip bulunamadi: https://github.com/HIllya51/LunaTranslator/releases' }
        $zip = Join-Path $env:TEMP $varlik.name
        Bilgi ("LunaTranslator {0} indiriliyor ({1:N0} MB)..." -f $rel.tag_name, ($varlik.size / 1MB))
        Invoke-WebRequest $varlik.browser_download_url -OutFile $zip -UseBasicParsing
        $gecici = Join-Path $env:TEMP 'luna_ac'
        if (Test-Path $gecici) { Remove-Item $gecici -Recurse -Force }
        Expand-Archive $zip $gecici -Force
        $exe = Get-ChildItem $gecici -Recurse -Filter 'LunaTranslator.exe' | Select-Object -First 1
        if (-not $exe) { Dur 'Arsivde LunaTranslator.exe yok.' }
        New-Item -ItemType Directory -Force $LunaYolu | Out-Null
        Copy-Item "$($exe.DirectoryName)\*" $LunaYolu -Recurse -Force
        Tamam "LunaTranslator kuruldu: $LunaYolu"
    }
    while (Get-Process LunaTranslator -ErrorAction SilentlyContinue) {
        Uyari 'LunaTranslator acik. Tepsi simgesine sag tikla > Cikis (yoksa ayarlari kapanirken ezer).'
        Read-Host '  Kapattiktan sonra Enter' | Out-Null
    }
    $uc = Join-Path $LunaYolu 'userconfig'
    New-Item -ItemType Directory -Force $uc | Out-Null
    foreach ($f in 'mypost.py', 'selfbuild.py') { Copy-Item (Join-Path $Depo "luna\$f") (Join-Path $uc $f) -Force }
    Tamam 'Eklentiler kopyalandi (mypost.py, selfbuild.py)'

    $vars = JsonOku (Join-Path $LunaYolu 'LunaTranslator\defaultconfig\config.json')
    $c = JsonOku (Join-Path $uc 'config.json')
    # Metin kaynagi: yalnizca OCR
    $ss = AltNesne $c 'sourcestatus2'
    foreach ($k in $vars.sourcestatus2.PSObject.Properties.Name) { Ayarla (AltNesne $ss $k) 'use' ($k -eq 'ocr') }
    # OCR motoru: yalnizca secilen
    $ocr = AltNesne $c 'ocr'
    foreach ($k in $vars.ocr.PSObject.Properties.Name) { Ayarla (AltNesne $ocr $k) 'use' ($k -eq $ocrMotoru) }
    # Ceviri: yalnizca ozel cevirici (selfbuild). Digerleri acik kalirsa TV'ye her cumle birden fazla gider.
    $fy = AltNesne $c 'fanyi'
    foreach ($k in $vars.fanyi.PSObject.Properties.Name) { Ayarla (AltNesne $fy $k) 'use' ($k -eq 'selfbuild') }
    Ayarla $c 'autorun' $true
    Ayarla $c 'ocr_auto_method_v2' 'period'
    Ayarla $c 'ocr_interval' $(if ($ocrMotoru -eq 'SnippingTool') { 0.3 } else { 1.5 })
    Ayarla $c 'networktcpenable' $true
    Ayarla $c 'networktcpport' 2333
    if (-not $c.PSObject.Properties['ocrregions2'] -or -not $c.ocrregions2) {
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type 'using System.Runtime.InteropServices; public class Dpi { [DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); }' -ErrorAction SilentlyContinue
        [Dpi]::SetProcessDPIAware() | Out-Null
        $e = [Windows.Forms.Screen]::PrimaryScreen.Bounds
        $b = @([int]($BOLGE_ORAN[0] * $e.Width), [int]($BOLGE_ORAN[1] * $e.Height), [int]($BOLGE_ORAN[2] * $e.Width), [int]($BOLGE_ORAN[3] * $e.Height))
        Ayarla $c 'ocrregions2' @(, $b)
        Tamam ("OCR bolgesi ({0}x{1} ekran): {2}" -f $e.Width, $e.Height, ($b -join ','))
    } else { Bilgi 'OCR bolgesi zaten secilmis, dokunulmadi.' }
    JsonYaz $c (Join-Path $uc 'config.json')

    $pp = JsonOku (Join-Path $uc 'postprocessconfig.json')
    Ayarla (AltNesne $pp '_11') 'use' $true
    JsonYaz $pp (Join-Path $uc 'postprocessconfig.json')
    Tamam 'Luna ayarlari: OCR, filtre, ozel cevirici, ag servisi (2333)'

    $anahtar = Read-Host '  Gemini API anahtari (istege bagli; bos = yalnizca Google)' -AsSecureString
    $anahtar = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($anahtar)).Trim()
    if ($anahtar -and $anahtar.Length -lt 20) {
        # Yanlislikla basilan tus (anahtar yerine tek karakter) Gemini'yi sessizce bozuyordu
        Uyari "Bu bir Gemini anahtari degil ($($anahtar.Length) karakter); Gemini ayarlanmadi. Anahtar AQ. ya da AIza ile baslar."
        $anahtar = ''
    }
    if ($anahtar) {
        $ts = JsonOku (Join-Path $uc 'translatorsetting.json')
        $a = AltNesne (AltNesne $ts 'chatgpt-3rd-party') 'args'
        Ayarla $a 'API接口地址' 'https://generativelanguage.googleapis.com'
        Ayarla $a 'SECRET_KEY' $anahtar
        Ayarla $a 'model' 'gemini-flash-lite-latest'
        Ayarla $a '使用自定义promt' $true
        Ayarla $a '自定义promt' $GEMINI_PROMPT
        JsonYaz $ts (Join-Path $uc 'translatorsetting.json')
        Tamam 'Gemini ayarlandi (cevirici olarak ACILMADI; selfbuild.py ayarlarini oradan okur)'
    } else { Bilgi 'Gemini yok: yalnizca Google Ceviri kullanilacak.' }
}

# ---------------------------------------------------------------- 5. Guvenlik duvari
if (Adim 'guvenlik') {
    Baslik '5/8 Windows Guvenlik Duvari (TCP 2333)'
    if (Get-NetFirewallRule -DisplayName 'xbox-samsung-subtitles-tv 2333' -ErrorAction SilentlyContinue) { Tamam 'Kural zaten var' }
    else {
        Bilgi 'Acilan pencerede "Evet" deyin (yonetici izni).'
        Start-Process cmd -ArgumentList '/c', "`"$PSScriptRoot\1_guvenlik_duvari_izni.bat`"" -Verb RunAs -Wait
        if (Get-NetFirewallRule -DisplayName 'xbox-samsung-subtitles-tv 2333' -ErrorAction SilentlyContinue) { Tamam 'Kural eklendi' }
        else { Uyari 'Kural eklenemedi; TV PC''ye baglanamayabilir. scripts\1_guvenlik_duvari_izni.bat dosyasini sonra calistirin.' }
    }
}

# ---------------------------------------------------------------- 6. TV baglantisi
$tvIp = $null
if (Adim 'tv') {
    Baslik '6/8 Samsung TV baglantisi'
    Bilgi "TV'de: Uygulamalar ekrani > kumandayla 1 2 3 4 5 > Developer Mode: On"
    Bilgi 'Host PC IP olarak bunu girin, sonra TV''yi tamamen kapatip acin:'
    PcIpleri | ForEach-Object { Write-Host "      $_" -ForegroundColor White }
    Read-Host '  Hazir olunca Enter' | Out-Null
    $tvIp = TvIp
    for ($i = 0; ; $i++) {
        Yerel "`"$SDB`" connect $tvIp" | Out-Null
        if ((Yerel "`"$SDB`" devices") -match [regex]::Escape($tvIp)) { Tamam "TV bagli: $tvIp"; break }
        Uyari "TV'ye baglanilamadi ($tvIp). TV acik mi, gelistirici modu ve Host PC IP dogru mu, ayni agda misiniz?"
        $yeni = (Read-Host '  Tekrar denemek icin Enter, IP degistiyse yeni IP, cikmak icin q').Trim()
        if ($yeni -eq 'q') { exit 1 }
        if ($yeni) { $tvIp = $yeni; Set-Content (Join-Path $PSScriptRoot 'tv_ip.txt') $tvIp -Encoding ASCII }
    }
}

# ---------------------------------------------------------------- 7. Samsung sertifikasi
if (Adim 'sertifika') {
    Baslik '7/8 Samsung sertifikasi'
    $profiller = 'C:\tizen-studio-data\profile\profiles.xml'
    $varMi = { (Test-Path $profiller) -and (Select-String -Path $profiller -SimpleMatch "name=`"$PROFIL`"" -Quiet) }
    if (& $varMi) { Tamam "Sertifika profili var: $PROFIL" }
    else {
        $launcher = Get-ChildItem "$CM\plugins" -Filter 'org.eclipse.equinox.launcher_*.jar' | Select-Object -Last 1
        Start-Process "$TZ\jdk\bin\javaw.exe" -WorkingDirectory $CM -ArgumentList '-Duser.language=en', '-Duser.country=US', '-Dfile.encoding=UTF-8', '-jar', $launcher.FullName
        Bilgi 'Sertifika Yoneticisi aciliyor (10-20 sn). Pencerede:'
        Bilgi "  + > Samsung > TV > profil adi: $PROFIL"
        Bilgi '  Author: yeni olustur > ad ve sifre belirle > tarayicida Samsung hesabinla giris'
        Bilgi '  Distributor: Privilege Public > DUID listesinde TV otomatik gelir > Next > Finish'
        while (-not (& $varMi)) { Read-Host '  Bitince Enter' | Out-Null; if (-not (& $varMi)) { Uyari "Profil '$PROFIL' henuz yok." } }
        Tamam "Sertifika profili olusturuldu: $PROFIL"
    }
}

# ---------------------------------------------------------------- 8. Derle, imzala, TV'ye yukle
if (Adim 'yukle') {
    Baslik "8/8 TV uygulamasini yukle"
    if (-not $tvIp) { $tvIp = TvIp; Yerel "`"$SDB`" connect $tvIp" | Out-Null }
    $proje = Join-Path $Depo 'tv-app'
    $sonuc = Join-Path $proje '.buildResult'
    if (Test-Path $sonuc) { Remove-Item $sonuc -Recurse -Force }
    $c1 = & cmd /c "`"$TIZEN`" build-web -- `"$proje`" 2>&1" | Out-String
    if ($c1 -notmatch 'BUILD SUCCESSFUL') { Write-Host $c1; Dur 'Derleme basarisiz.' }
    $c2 = & cmd /c "`"$TIZEN`" package -t wgt -s $PROFIL -- `"$sonuc`" 2>&1" | Out-String
    $wgt = Get-ChildItem $sonuc -Filter *.wgt | Select-Object -First 1
    if (-not $wgt) { Write-Host $c2; Dur "Paketleme basarisiz ('$PROFIL' sertifika profili var mi?)." }
    if ($wgt.Name -ne 'AltyaziTV.wgt') { Rename-Item $wgt.FullName 'AltyaziTV.wgt' }   # bosluklu ad install'u bozuyor
    $c3 = & cmd /c "`"$TIZEN`" install -n AltyaziTV.wgt -s ${tvIp}:26101 -- `"$sonuc`" 2>&1" | Out-String
    if ($c3 -notmatch 'successfully installed') { Write-Host $c3; Dur 'TV''ye yuklenemedi.' }
    Tamam 'TV''ye yuklendi'
    & cmd /c "`"$TIZEN`" run -p $APPID -s ${tvIp}:26101 2>&1" | Out-Null
    Tamam 'TV''de Altyazi TV baslatildi'
}

Baslik 'Bitti'
Bilgi '1. Xbox uygulamasi > konsol > Uzaktan oynat > pencereyi TAM EKRAN ve EN ONDE tut.'
Bilgi '2. LunaTranslator''i ac.'
Bilgi '3. TV''de Altyazi TV PC''yi agda kendisi bulur. Bulamazsa KIRMIZI > PC IP''sini gir (nokta icin OK) > KIRMIZI ile kaydet:'
PcIpleri | ForEach-Object { Write-Host "      $_" -ForegroundColor White }
Bilgi '4. Oyun kumandasini PC''ye bagla; goruntuyu TV''den izle.'
Read-Host '  Kapatmak icin Enter' | Out-Null
