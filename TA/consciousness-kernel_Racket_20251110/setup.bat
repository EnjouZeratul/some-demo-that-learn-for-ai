@echo off
cd /d D:\TA\consciousness-kernel_Racket_20251110
set PLT_PKG_SCOPE=installation
set PLTUSERHOME=%cd%\racket-env
D:\TA\Racket\raco.exe pkg install --auto http-easy dotenv
pause
