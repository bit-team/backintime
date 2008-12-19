#!/bin/bash
xgettext --output=- *.py *.glade | msggrep -v -K -e "gtk-" > messages.pot
