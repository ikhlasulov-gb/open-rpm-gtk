#!/usr/bin/env python3
import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw
from window import OpenRpmApp


def main(version):
    app = OpenRpmApp()
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main('1.0.0'))
