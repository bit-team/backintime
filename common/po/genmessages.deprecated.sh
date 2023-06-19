#!/bin/bash
xgettext --output=- ../../common/*.py ../../qt/*.py > messages.pot
