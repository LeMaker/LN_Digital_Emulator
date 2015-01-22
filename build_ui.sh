#!/bin/bash
#: Description: builds the ui for LN_Digital_Emulator

rcsource="src/LN_Digital_Emulator.qrc"
rcfile="LN_Digital_Emulator/LN_Digital_Emulator_rc.py"
uisource="src/LN_Digital_Emulator.ui"
uifile="LN_Digital_Emulator/LN_Digital_Emulator_ui.py"

printf "Generating resource.\n"
pyside-rcc $rcsource -o $rcfile -py3
printf "Generating UI.\n"
pyside-uic $uisource -o $uifile

# pyside doesn't know about Python submodules
printf "Fixing UI.\n"
string="import LN_Digital_Emulator_rc"
replace="import LN_Digital_Emulator.LN_Digital_Emulator_rc"
sed -e "s/$string/$replace/" $uifile >> /tmp/LN_Digital_Emulator_ui_file
mv /tmp/LN_Digital_Emulator_ui_file $uifile
