Memento Mori Game API Client & Utilities
########################################

Installation
************

If you are using Windows, you should install `Git <https://git-scm.com/download/win>`__ for the easiest way to keep
up with the latest updates.  It is strongly recommended to use the Bash shell that comes with Git ("Git Bash") when
you run Git commands or these scripts.  All further instructions will assume you are using Bash.

Clone the this repo and install its dependencies (
`using a venv <https://realpython.com/python-virtual-environments-a-primer/>`__ is recommended)::

    git clone https://github.com/brellorand/memento-mori-client.git
    cd memento-mori-client
    python -m venv venv
    . venv/Scripts/activate  # This is for Windows - for Linux: . venv/bin/activate
    pip install -e .


Python Version Compatibility
============================

Python 3.11 or above is required.  So far, this code has only been tested using Python 3.12.


Scripts
*******

- ``assets.py``: Download bundle files and extract assets (images, audio, etc) from them
- ``catalog.py``: Download basic master/asset catalog info
- ``runes.py``: (WIP / incomplete) Calculate rune stat totals and ticket costs
