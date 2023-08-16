# Using Sphinx to write and build documentation
<sub>Feel free to [open issues](https://github.com/bit-team/backintime/issues) or contact the [maintenance team on the mailing list](https://mail.python.org/mailman3/lists/bit-dev.python.org/) if this text is difficult to understand or not helpful.</sub>

This file describes briefly how to
- build and view the source code "API" documentation of _Back In Time_
  "common" (CLI)
- add new modules to the documentation
- write docstrings
- known issues with documentation generation

## Index

<!-- TOC start -->
- [Background](#background)
- [Why to use Sphinx to generate the
  documentation?](#why-to-use-sphinx-to-generate-the-documentation)
- [How to build and view the
  documentation](#how-to-build-and-view-the-documentation)
- [How to add new modules to the
  documentation](#how-to-add-new-modules-to-the-documentation)
- [How to write docstrings for Back In
  Time](#how-to-write-docstrings-for-back-in-time)
- [Commonly used rst markups in the
  docstring](#commonly-used-rst-markups-in-the-docstring)
- [Known issues with documentation
  generation](#known-issues-with-documentation-generation)
<!-- TOC end -->

# Background

The documentation is generated automatically from the docstrings
in the python source code files using the tool

  Sphinx (https://www.sphinx-doc.org/en/master/)

together with the Sphinx-Extensions

  - autodoc (to automatically generate rst doc files from the python docstrings)
    https://www.sphinx-doc.org/en/master/man/sphinx-apidoc.html

  - napoleon (to convert google-style docstrings to reStructuredText "rst" format required for autodoc)
    https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html

  - viewcode (to create links to browse the highlighted source code)
    https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html

For a brief introduction to Sphinx for Python see:
https://betterprogramming.pub/auto-documenting-a-python-project-using-sphinx-8878f9ddc6e9

For a reference of rst markups see:
https://docutils.sourceforge.io/docs/user/rst/quickref.html

For a description of the Google coding style for python see:
https://google.github.io/styleguide/pyguide.html

# Why to use Sphinx to generate the documentation?

Sphinx has eg. the advantage to

- generate the documentation in different formats
  (eg. html, PDF or Linux man pages).

- report invalid markups contained in the documentation

- inject documentation of attributes and methods from parent classes
  into sub classes (in case of inheritance)



# How to build and view the documentation

Open a terminal in the "doc-dev" folder and call

    make html      # to generate the HTML documentation
    make htmlOpen  # to open the browser showing the generated HTML pages



# How to add new modules to the documentation

There are two scenarios here:



a) The new module files are in a separate folder (not yet included in the doc generation so far)

- Add the python source code folder to the doc-dev/conf.py file
  so that autodoc can find the files (navigate "relative" to the "doc-dev" folder)

- Generate the initial rst files for the new modules via "sphinx-apidoc", eg.

      sphinx-apidoc -o ./plugins ../plugins

  to create a sub folder "doc-dev/plugins" with the rst files (one for each source file
  in "doc-dev/../plugins"

- Add the new modules in the sub folder to the top-most "root" index.rst:

  # under "modules.rst" add this line add a link to new modules
  plugins/modules.rst



b) The new module files are in a folder that already contains other modules contained in the doc

   To create the initial version of rst files for new modules eg. in the "common" folder use

       sphinx-apidoc -o . ..

   TODO: How to remove old rst files with non-existing python files (eg. due to renaming or deletion)
         -> probably the -f ("force") argument could do this. Try it with -d ("dry-run")!



# How to write docstrings for _Back In Time_

_Back In Time_ uses the [Google style for
docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings).
Please stick to this convention. Look into documentation of
[`sphinx.ext.napoleon` for an extended
example](https://www.sphinx-doc.org/en/master/usage/extensions/example_google.html#example-google).


# Commonly used rst markups in the docstring

Despite using the Google docstring style rst markups can and should still
be used to format text and cross-reference code.

- Reference a class (with namespace if not in the same):

      :py:class:`pluginmanager.PluginManager`

  Important: Don't forget to surround the function name with back ticks
  otherwise Sphinx will not create a cross reference silently!

- Reference a method/function:

      :py:func:`takeSnapshot`

  Important: Don't forget to surround the function name with back ticks
  otherwise Sphinx will not create a cross reference silently!

- Specify the python type of an method/function argument:

  Add the type name (with namespace if not in the same) in parentheses

    Args:
        cfg (config.Config): Current configuration

- Indicate python keywords (without cross-referencing them)

      ``True``
      ``None``

  Surround the keyword with two backticks (it will be shown as code then)



# Known issues with documentation generation

- Sphinx' "make html" does not recreate the html file of a sub class if only
  the parent class docstring was changed.

  Impact: Inherited documentation in the sub class is not up to date

  Work around: Use "make clean" before "make html"

<sub>March 2023</sub>
