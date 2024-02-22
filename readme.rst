Memento Mori Game API Client & Utilities
########################################

Installation
************

If you are using Windows, you should install `Git <https://git-scm.com/download/win>`__ for the easiest way to keep
up with the latest updates.  It is strongly recommended to use the Bash shell that comes with Git ("Git Bash") when
you run Git commands or these scripts.  All further instructions will assume you are using Bash.

Clone the this repo and install its dependencies (
`using a venv <https://realpython.com/python-virtual-environments-a-primer/>`__ is recommended)::

    mkdir ~/git
    cd ~/git
    git clone https://github.com/brellorand/memento-mori-client.git
    cd memento-mori-client
    python -m venv venv
    . venv/Scripts/activate  # This is for Windows - for Linux: . venv/bin/activate
    pip install -e .


After initial installation, to use these scripts again in a new Bash session, there are fewer steps::

    cd ~/git/memento-mori-client
    . venv/Scripts/activate  # This is for Windows - for Linux: . venv/bin/activate


When an update is available, you can use a git command to download the latest changes::

    cd ~/git/memento-mori-client
    . venv/Scripts/activate  # This is for Windows - for Linux: . venv/bin/activate
    git pull


Python Version Compatibility
============================

Python 3.11 or above is required.  So far, this code has only been tested using Python 3.12.


Scripts
*******

Scripts are in the ``bin`` directory.  The current scripts that are available:

- ``assets.py``: Download bundle files and extract assets (images, audio, etc) from them
- ``catalog.py``: Download basic master/asset catalog info
- ``runes.py``: (WIP / incomplete) Calculate rune stat totals and ticket costs

Use ``--help`` to see more info about the options they support.  Example::

    $ bin/assets.py --help
    usage: assets.py {list|save|index|find|extract} [--no-cache] [--verbose [VERBOSE]] [--help]

    Memento Mori Asset Manager

    Subcommands:
      {list|save|index|find|extract}
        list                      List asset paths
        save                      Save bundles/assets to the specified directory
        index                     Create a bundle index to facilitate bundle discovery for specific assets
        find                      Find bundles containing the specified paths/files
        extract                   Extract assets from a .bundle file

    Optional arguments:
      --no-cache, -C              Do not read cached game/catalog data
      --verbose [VERBOSE], -v [VERBOSE]
                                  Increase logging verbosity (can specify multiple times)
      --help, -h                  Show this help message and exit


Each subcommand/action may have additional ``--help`` text.
