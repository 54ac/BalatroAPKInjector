## Balatro APK Injector

### What is this?

This is a simple Python script that injects the Android build of [Lovely](https://github.com/kodenamekrak/lovely-injector) to the retail APK of Balatro, adding mod support to the game. Primarily written to be used with the [Mobile Menu Mod](https://github.com/54ac/BalatroMobileMenuMod) mod, but should work with others as long as they were written for the mobile version of the game.

### Requirements

- Python 3
- Balatro APK, which can be copied from your device with apps such as [App Manager](https://f-droid.org/en/packages/io.github.muntashirakon.AppManager/).

### Usage

- [Download the script](https://raw.githubusercontent.com/54ac/BalatroAPKInjector/refs/heads/main/apk_patcher.py) and place it in a folder with the Balatro APK.
- Open a terminal in that folder and run e.g. `python apk_patcher.py balatro.apk`, optionally providing additional arguments which are listed when running the script with the `--help` flag. The script will set up a virtual environment and take care of downloading and setting up all dependencies automatically.
- Install the resulting APK on your device, e.g. by using adb (`adb install path/to/balatro.mod.apk`).
- Depending on your device, the data folder may be located at `/storage/emulated/0/Android/data/com.playstack.balatro.android.mod` or its equivalent on external storage (SD card). Copy mods to the `files/mods` folder inside.

### Notes

Mods or frameworks such as Steamodded might not work at this time, as they are designed for the PC version of the game.
