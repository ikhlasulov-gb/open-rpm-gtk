#!/bin/bash
OUTPUT="po/site.ikhlasulov.openrpm.pot"
PACKAGE_NAME="site.ikhlasulov.openrpm"
ENCODING="UTF-8"
LINGUAS_FILE="po/LINGUAS"

# create pot
xgettext --files-from=po/POTFILES \
         --output="$OUTPUT" --package-name="$PACKAGE_NAME" \
         --from-code="$ENCODING" --add-comments \
         --keyword=_ --keyword=C_:1c,2

sed -i 's/charset=CHARSET/charset=UTF-8/g' $OUTPUT

sed -i '2,3c\
# Copyright (C) 2026 Ikhlashulov\
# This file is distributed under the license GPLv3-or-later.' $OUTPUT
