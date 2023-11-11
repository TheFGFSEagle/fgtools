# FGTools
Tools for creating, managing and editing FlightGear scenery, aircraft, …

## Installation
_Note_: To run these scripts you need Python 3, Python 2 won't work. Recommended version is 3.10 as I only have that installed so couldn't test with any other versions - earlier 3.x versions should work, but no guarantee !

### Normal user / Official releases
The latest release of FGTools can be installed with `pip`:
```sh
pip install fgtools
```

### Developers
If you want to always have the latest bleeding edge code, or want to contribute, you should install from Git:

`git clone` this repo and put it in a place of your choice, say `/home/user/fgtools`:
```sh
/home/user$ git clone https://github.com/TheFGFSEagle/fgtools
```
Then, `cd` into the cloned repo folder and install the code:
```sh
cd fgtools
pip install -e .
```
To update the code, you'd run (from the same folder):
```sh
git pull
```

## Scripts

* Aircraft
    * javaprop2jsbcpct
    * vsphist2jsbtable
    * vspstab2jsbtable
* Miscellaneous
    * coord_converter
    * scrape_emanualonline
    * scrape_scribd
    * tabletool
* Scenery
    * aptdat2airportsxml
    * create_day_night_xml
    * dsftxt2stg
    * edit_stg
    * fix_aptdat_icaos
    * genws20
    * osm2aptdat
    * pull_xplane_aptdat
    * stg2ufo
    * ungap_btg

## Credits
* dsftxt2stg-lookup.py taken and modified from https://github.com/mherweg/d-laser-fgtools/library.txt
