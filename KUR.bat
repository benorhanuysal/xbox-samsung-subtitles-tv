@echo off
rem Tek tik kurulum: scripts\kurulum.ps1 (Tizen SDK, Samsung eklentileri, LunaTranslator, TV uygulamasi).
rem Tekrar calistirmak guvenli: yapilmis adimlari atlar.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\kurulum.ps1" %*
