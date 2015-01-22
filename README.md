LN_Digital_Emulator
===================

An emulator for the LN Digital I/O board.

Install
=======

Dowdload the source code package from Lemaker Github, unzip::

    $ cd LN_Digital_Emulator

Manual Install `LN_Digital_Emulator` (for Python 3) with the following command::

    $ sudo python3 setup.py install

Manual Install `LN_Digital_Emulator` (for Python 2) with the following command::

    $ sudo python setup.py install

Use
===

Run the emulator with the Desktop icon::LN-Digital-Emulator, or

    $ cd /usr/local/bin
    $ sudo LN-Digital-Emulator

Development Notes
=================

UI built with [qt4-designer](http://doc.qt.digia.com/4.0/qt4-designer.html).
To generate the UI files, run:

    build_ui.sh
