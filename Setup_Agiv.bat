@echo on
::set AGIVBENCHPATH=^Z:\W10\A puissance 3\AGIV_Bench%
set INSTALLPATH=%cd%
set AGIVBENCHPATH=^C:\AGIV_Bench%
xcopy "%INSTALLPATH%\AGIV_Bench" "%AGIVBENCHPATH%" /E /I /Y
set PYTHON_VERSION=3.8.1
:: -----------------------------------------------------------
:: Script d'installation conditionnelle de Python + actions post-installation
:: -----------------------------------------------------------

set PYTHON_INSTALL_DIR=C:\Python381
set ORIGPATH=%PATH%
set "PATH=%PATH%;%PYTHON_INSTALL_DIR%;%PYTHON_INSTALL_DIR%\Scripts"

:: Vérifier si Python est déjà installé
"%PYTHON_INSTALL_DIR%/python" --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Python est déjà installé.
    goto POST_INSTALL
) else (
    echo [INFO] Python n'est pas installé. Début de l'installation...
)

:: Installer Python silencieusement
echo [ETAPE] Installation dans %PYTHON_INSTALL_DIR%...
%INSTALLPATH%\python-3.8.10-amd64.exe  /quiet InstallAllUsers=1 PrependPath=1 TargetDir="%PYTHON_INSTALL_DIR%" Include_launcher=1


:: Vérification post-installation
"%PYTHON_INSTALL_DIR%/python" --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] L'installation a échoué.
    pause
    exit /b 1
)

echo [SUCCES] Python %PYTHON_VERSION% a été installé avec succès.

:: Actions post-installation (exemples)
:POST_INSTALL
echo.
echo [INFO] Début des actions post-installation...

echo [INFO] Installation des packages python
"%PYTHON_INSTALL_DIR%/Scripts/pip" install --no-index --find-links="%INSTALLPATH%\AGIV_used_packages" -r requirements.txt
echo [INFO] Creation icones de lancement Agiv
mkdir "%USERPROFILE%\icons"
copy "%AGIVBENCHPATH%\Agiv\icons\GIV4.ico" "%USERPROFILE%\icons"
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\createshortcut.vbs"
echo sLinkFile = "%USERPROFILE%\Desktop\StartAgivPJ.lnk" >> "%TEMP%\createshortcut.vbs"
echo Set oLink1 = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\createshortcut.vbs"
echo oLink1.TargetPath = "%AGIVBENCHPATH%\StartAgivCalys.bat"  >> "%TEMP%\createshortcut.vbs"
echo oLink1.IconLocation = "%USERPROFILE%\icons\GIV4.ico"   >> "%TEMP%\createshortcut.vbs"
echo oLink1.Save >> "%TEMP%\createshortcut.vbs"

echo sLinkFile = "%USERPROFILE%\Desktop\StartAgivCalys.lnk" >> "%TEMP%\createshortcut.vbs"
echo Set oLink2 = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\createshortcut.vbs"
echo oLink2.TargetPath = "%AGIVBENCHPATH%\StartAgivCalys.bat"  >> "%TEMP%\createshortcut.vbs"
echo oLink2.IconLocation = "%USERPROFILE%\icons\GIV4.ico"   >> "%TEMP%\createshortcut.vbs"
echo oLink2.Save >> "%TEMP%\createshortcut.vbs"
cscript /nologo "%TEMP%\createshortcut.vbs"
del "%TEMP%\createshortcut.vbs"
echo [INFO] Installation du driver CALYS
set DRIVERPATH=^%TEMP%\CalysDriver%
mkdir %DRIVERPATH%
tar -xf "%AGIVBENCHPATH%/CP210x_Universal_Windows_Driver.zip" -C "%DRIVERPATH%"
pnputil /add-driver "%DRIVERPATH%\silabser.inf" /install /force

set PATH=%ORIGPATH%

:: Fin du script
echo.
echo [INFO] Toutes les actions ont été exécutées.
pause
