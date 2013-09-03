# Nox Spell Server: Python Aspell server
Originally from http://orangoo.com/labs/GoogieSpell/Download/Nox_Spell_Server/

This fork forces the use of Aspell in all cases.

Added daemonized server, now it can be started or stopped as a daemon.

## How to use it

- make sure you have Aspell installed with the dictionnaries you need. (on Ubuntu, for English only: `sudo apt-get install aspell-en`)
- git clone this repo
- cd into the cloned repo
- run `python nox_server.py start`, by default starts listening on port 14003
- you can now use it from GoogieSpell!
- Usage is: `python nox_server.py [start|stop|restart] PORT pid-uri`. PORT and pid-uri are optional, defaults are 14003 and /tmp/nox_server.pid.
