# Nox Spell Server: Python Aspell server
Originally from http://orangoo.com/labs/GoogieSpell/Download/Nox_Spell_Server/

This fork forces the use of Aspell in all cases.

## How to use it

- make sure you have Aspell installed with the dictionnaries you need. (on Ubuntu, for English only: `sudo apt-get install aspell-en`)
- git clone this repo
- cd into the cloned repo
- run `python nox_server.py 14003` where 14003 is the port number
- you can now use it from GoogieSpell!