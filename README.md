# fgtools
Tools for creating, managing and editing FlightGear scenery, aircraft, …

## Installation
To run these scripts you need Python 3, Python 2 won't work. Tested with Python 3.8 and 3.11 - earlier 3.x versions should work, but no guarantee!

### Linux
Download / `git clone` this repo and put it in a place of your choice, say `/home/user/fgtools`. With `git clone`, you would use this command:
```sh
/home/user$ git clone https://github.com/TheFGFSEagle/fgtools
```
Before you run the scripts you have to make sure that this repository on your local disk (here `/home/user/fgtools`) is inside your `PYTHONPATH` environment variable, or you must run the scripts from inside `/home/user/fgtools`. To add the folder to your `PYTHONPATH`, use this command:
```sh
export PYTHONPATH="${PYTHONPATH}:/home/user/fgtools"
```
Note: this is lost when you close the terminal / console, so you have to run this command every time you open a new console and run the scripts from it. To make the change persistent, add the command to the end of the `.profile` file in your home folder.

### Windows

Download or `git clone` this repo and put it in a place of your choice, say `C:\Users\YOURUSERNAME\Desktop`. With `git clone`, you would use this command:

```console
git clone https://github.com/TheFGFSEagle/fgtools
```

Copy the file of the python script you want to use and paste it in the repository folder (outside of the subfolders).

ensure scipy is installed:

```console
python -m pip install scipy
```

run the python file:

```console
python pythonfilename.py
```
## Credits
* dsftxt2stg-lookup.py taken and modified from https://github.com/mherweg/d-laser-fgtools/library.txt
