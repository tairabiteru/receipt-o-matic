# Receipt-O-Matic
A simple program to allow easy printing of receipts for the NDL makerspace.

We've got a bunch of Star TSP printers here at the library for receipt printing, and I decided to start using one in our makerspace for receipt printing. Partly for fun, but mostly to spare the circulation department from my chicken scratch handwriting.

## Installation
This program is used in production as a compiled binary with [PyInstaller](https://pyinstaller.org/en/stable/). The specific command I use is as follows:
```
pyinstaller --onefile --add-data="assets/makeit.png;assets" --add-data="assets/capabilities.json;assets" __main__.py
```
This command adds two assets to the binary, a PNG image used in the header of receipts, and a `capabilities.json` file which details the capabilities of our specific printer to the serial connection library. After compilation, the binary can be moved into its own directory, anywhere that's convienient in the file system.

A TOML file named `settings.toml` should be created in the same directory as the binary, and should contain the following information, customized of course to your needs:
```TOML
# Serial port of the printer, Ex. "COM10"
SERIAL_PORT = "serial_port_here"

# $0.05 per gram of filament.
FILAMENT_RATE = 0.05

# $0.50 per page.
SUBLIMATION_RATE = 0.50

# $3.00 per mug.
MUG_RATE = 3.00
```
