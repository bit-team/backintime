# Using Sphinx to write and build documentation
<sub>Feel free to [open issues](https://github.com/bit-team/backintime/issues)
or contact the
[maintenance team on the mailing
list](https://mail.python.org/mailman3/lists/bit-dev.python.org/)
if this text is difficult to understand or not helpful.</sub>

This file describes briefly how to
- build and view the source code "API" documentation of _Back In Time_
  "common" (CLI)
- add new modules to the documentation
- write docstrings
- known issues with documentation generation

## Index

<!-- TOC start -->
- [Background](#background)
- [How to build and view the documentation](#how-to-build-and-view-the-documentation)
- [How to write docstrings for Back In Time](#how-to-write-docstrings-for-back-in-time)
- [How to add new modules to the documentation](#how-to-add-new-modules-to-the-documentation)
- [Commonly used rst markups in the docstring](#commonly-used-rst-markups-in-the-docstring)
- [Known issues with documentation generation](#known-issues-with-documentation-generation)
<!-- TOC end -->

# Background

The documentation is generated automatically from the docstrings in the python
source code files using [Sphinx](https://www.sphinx-doc.org/en/master/) in
combination with the following Sphinx-Extensions:

  - [autodoc](https://www.sphinx-doc.org/en/master/man/sphinx-apidoc.html) to
    automatically generate rst doc files from the python docstrings.
  - [napoleon](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html)
    to convert google-style docstrings to reStructuredText `rst` format
    required for autodoc.
  - [viewcode](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html)
    to create links to browse the highlighted source code.

Further readings:

 - [Brief introduction to Sphinx for Python](https://betterprogramming.pub/auto-documenting-a-python-project-using-sphinx-8878f9ddc6e9)
 - [Quick reference of rst markups](https://docutils.sourceforge.io/docs/user/rst/quickref.html)
 
# How to build and view the documentation

Open a terminal, navigate to the folder `common/doc-dev` and call

    make html      # to generate the HTML documentation
    make htmlOpen  # to open the browser showing the generated HTML pages

# How to write docstrings for _Back In Time_

_Back In Time_ uses the [Google style for
docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings).
Please stick to this convention. Look into documentation of
[`sphinx.ext.napoleon`](https://www.sphinx-doc.org/en/master/usage/extensions/example_google.html#example-google)
for extended examples.

# How to add new modules to the documentation

There are two scenarios:

## Scenario A: New module files are in a separate folder (not yet included in the doc generation so far)

- Add the python source code folder to the file `doc-dev/conf.py` which is the
  configuration. Then the `autodoc` extension is able to find the files
  (navigate _relative_ to the `doc-dev` folder).
- Generate the initial `.rst` files for the new modules via `sphinx-apidoc`, eg.

      sphinx-apidoc -o ./plugins ../plugins

  This example will create a sub folder `doc-dev/plugins` with the `.rst`
  files (one for each source file) in `doc-dev/../plugins`.
- Add the new modules in the sub folder to the top-most _root_ `index.rst`:

      # under "modules.rst" add this line add a link to new modules
      plugins/modules.rst

## Scenario B: The new module files are in a folder that already contains other modules contained in the doc

To create the initial version of `.rst` files for new modules eg. in the `common` folder use

       sphinx-apidoc -o . ..

_TODO_: How to remove old rst files with non-existing python files (eg. due to
renaming or deletion)? Probably the -f ("force") argument could do this. Try it
with -d ("dry-run")!

# Commonly used rst markups in the docstring

Despite using the Google docstring style rst markups can and should still
be used to format text and cross-reference code.

- Reference a class (with namespace if not in the same):

      :py:class:`pluginmanager.PluginManager`

  Important: Don't forget to surround the function name with back ticks
  otherwise Sphinx will not create a cross reference silently!

- Reference a method/function:

      :py:func:`takeSnapshot`

- Reference a module:

      :py:module:`datetime`

- Specify the python type of an method/function argument:

  Add the type name (with namespace if not in the same) in parentheses

      """Short description...
      
      Long description...
      
      Args:
          cfg (config.Config): Current configuration
      """

- To indicate verbatim text (inline code) enclose it with two backticks each.

      ``True``
      ``None``
      ``de_DE.UTF-8``


# Known issues with documentation generation

- Elements of PyQt can not be referenced. It is a [known
  Issue](https://riverbankcomputing.com/pipermail/pyqt/2013-March/032528.html)
  without an acceptable solution. Name them via verbatime text (two backticks)
  only.
  
- Sphinx' ``make html`` does not recreate the html file of a sub class if only
  the parent class docstring was changed.

  _Impact_: Inherited documentation in the sub class is not up to date

  _Work around_: Use ``make clean`` before ``make html``

<sub>May 2024</sub>
