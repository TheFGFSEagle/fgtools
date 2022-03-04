# fgtools
Tools for creating, managing and editing FlightGear scenery, aircraft, …

## Installation
To run these scripts you need Python 3, Python 2 won't work. Recommended version is 3.8 as I only have that installed so couldn't test with any other versions - earlier 3.x versions should work, but no guarantee !

### Linux
Download / `git clone` this repo and put it in a place of your choice, say `/home/user/fgtools`. With `git clone`, you would use this command:
```sh
/home/user$ git clone https://github.com/TheFGFSEagle/fgtools
```
Before you run the scripts you have to make sure that the folder containing this repository on your local disk (here `/home/user`) is inside your `PYTHONPATH` environment variable, or you must run the scripts from inside the `fgtools` folder. To add the folder to your `PYTHONPATH`, use this command:
```sh
export PYTHONPATH="${PYTHONPATH}:/home/user"
```
Note: this is lost when you close the terminal / console, so you have to run this command every time you open a new console and run the scripts from it. To make the change persistent, add the command to the end of the `.profile` file in your home folder.

### Windows
_I don't have Windows so cannot provide any instructions - contributions by Windows users welcome !_

