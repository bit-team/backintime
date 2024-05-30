This directory contains the source files for various types of documentation
for _Back In Time_.

- `manual`: User Manual

### How to reduce file size of images
For PNG images `optipng` could be used. *Attention*: By default it overwrites
the original files. The following command use the highest possible optimization
and write the result in a subfolder.

    $ optipng --dir subfolder -o7 *.png

As an alternative `pngcrush` can be used. The following determine the best
algorithm by its own.

    $ pngcrush -d subfolder -brute *.png

Applied to a set of _Back In Time_ dark mode screenshots, their file size
was reduced by approximately 13%. Both applications show no significant
differences. The visual result is indistinguishable from the original.
