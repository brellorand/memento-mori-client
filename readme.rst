Memento Mori Game API Client & Utilities
########################################

Installation
************

If you are using Windows, you should install `Git <https://git-scm.com/download/win>`__ for the easiest way to keep
up with the latest updates.  It is strongly recommended to use the Bash shell that comes with Git ("Git Bash") when
you run Git commands or these scripts.  All further instructions will assume you are using Bash.

Clone the this repo and install its dependencies (`using a venv
<https://realpython.com/python-virtual-environments-a-primer/>`__ is recommended)::

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
- ``game.py``: Perform actions that require logging in to a specific account + world
- ``gear.py``: Calculate misc info about gear
- ``mb.py``: Download raw data referenced by ``DownloadRawDataMB`` and view info from other MB files
- ``runes.py``: (WIP / incomplete) Calculate rune stat totals and ticket costs
- ``speed.py``: Calculate rune levels required to speed tune a given party

Use ``--help`` to see more info about the options they support.  Example::

    $ bin/assets.py --help
    usage: assets.py {list|save|index|find|extract|convert} [--no-cache] [--config-file CONFIG_FILE] [--verbose [VERBOSE]] [--help]

    Memento Mori Asset Manager

    Subcommands:
      {list|save|index|find|extract|convert}
        list                      List asset paths
        save                      Save bundles/assets to the specified directory
        index                     Create a bundle index to facilitate bundle discovery for specific assets
        find                      Find bundles containing the specified paths/files
        extract                   Extract assets from a .bundle file
        convert                   Convert extracted audio assets to FLAC

    Optional arguments:
      --no-cache, -C              Do not read cached game/catalog data
      --config-file CONFIG_FILE, -cf CONFIG_FILE
                                  Config file path (default: ~/.config/memento-mori-client)
      --verbose [VERBOSE], -v [VERBOSE]
                                  Increase logging verbosity (can specify multiple times)
      --help, -h                  Show this help message and exit


Each subcommand/action may have additional ``--help`` text.


Game Interaction
================

The ``game.py`` script allows interaction with the game while logged in to a specific account + world.


Account Registration
--------------------

Account registration is a one-time action that needs to happen before you can use this project to interact with aspects
of the game that require being logged in to a specific account + world.  This is a one-time action - after initial
login, you should never need to complete this step again.

The first step to using it is to register a user ID and password.  This can be accomplished by using the ``login``
subcommand::

    game.py login --user-id 123456789 --name MyPhone


You can provide any name that you want to use later.  The ``--user-id`` value should match the numeric user ID for your
account, as is visible from the login screen.  This is NOT your ``Player ID`` that is visible when you are logged in to
a world.  If you are logged in to a specific world, then you need to click the hamburger / 3x horizontal line menu at
the top-right of the home screen, then click ``Return to Title`` to be able to access the correct value to enter here.

From the main title screen, click the Account Link icon (the inner-most icon of the two icons near the top-right of the
screen).  Under the ``Use Password`` section, click ``Link``, then click the ``Set`` button next to the
``Set link password`` option.  The value you should enter for the ``--user-id`` option is the value displayed as the
``Link Code`` in that prompt.  If you did not already set a password for your account, then you should set it now.  The
script will securely prompt you for your password, and it will then securely store a token that will be used for
subsequent logins.

If you find the login token in the config file, it is important that you never share that value with ANYONE.  It is
an irrevocable secret that will grant anyone who has it access to your account (similar to your account password.)

Game Actions
------------

After registering your account, you can use other functionality of ``game.py``, including subcommands for the following
actions::

    - Smelting
    - Tower battle
    - Quest battle
