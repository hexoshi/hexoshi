This file has been dedicated to the public domain, to the extent
possible under applicable law, via CC0. See
http://creativecommons.org/publicdomain/zero/1.0/ for more
information. This file is offered as-is, without any warranty.

========================================================================


HOW TO RUN

If you have downloaded a version of the game designated for a particular
system, simply run the executable.

To run the source code, you will need Python 3.6 or later
<https://www.python.org>. You will also need the dependencies listed in
requirements.txt, which you can install automatically by using the
following command:

    python3 -m pip install -r requirements.txt

Once you have installed the dependencies, you can start the game by
running "hexoshi.py". On most systems, this should be done by
double-clicking on it; if you are shown a dialog asking you if you want
to display or run the file, choose to run it.

There are some command-line options that can be passed. Run the game in
a terminal with the "-h" command-line option for more information.


NOTES FOR GIT REPO USERS

The Hexoshi Git repository excludes some automatically generated files,
so if you are running Hexoshi directly from the Git repository (rather
than a release archive), there are a couple extra steps to keep in mind.

Hexoshi uses gettext for translations. Building gettext files can be
done with the included build.py script in data/locale (requires msgfmt):

    cd data/locale
    ./build.py
    cd ../..

For startup efficiency, Hexoshi generates map files on first startup and
attempts to save them to Hexoshi's data directory (either the directory
passed via Hexoshi's -d argument, or the "data" directory in the same
location as hexoshi.py by default). If packaging Hexoshi for
distribution, these files should be pre-generated. You can do so easily
with the following command:

    ./hexoshi.py -mq

The -m option forces map generation, and the -q option causes the game
to quit immediately after opening. Alternatively, simply running the
game normally before distributing should work as long as no pre-existing
map files already exist.
