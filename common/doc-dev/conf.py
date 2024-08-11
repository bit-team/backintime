#!/usr/bin/env python3
import sys
import os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

sys.path.insert(0, os.path.abspath(os.path.join(os.pardir)))
sys.path.insert(0, os.path.abspath(os.path.join(os.pardir, "plugins")))

# -- General configuration ------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinx_rtd_theme'
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'BackInTime'
copyright = '2016, Germar Reitze'
author = 'Germar Reitze'

# Don't edit this variable. It is updated automatically by "updateversion.sh".
import backintime
version = backintime.__version__
# The full version, including alpha/beta/rc tags.
release = version  # '1.3.3-dev'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'private-members': True,
    'undoc-members': True,
    'special-members': True,
    'exclude-members': '__weakref__,__dict__,__module__,__annotations__',
}

# -- Intersphinx options --------------------------------------------------

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    # PyQt is not mappable because of a known issue. See
    # https://riverbankcomputing.com/pipermail/pyqt/2013-March/032528.html
}

# -- Napoleon include private members which have docstrings ---------------
napoleon_include_private_with_doc = True

# -- Options for HTML output ----------------------------------------------
# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
# html_theme = 'classic'
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y, %H:%M (%Z)'

# Output file base name for HTML help builder.
htmlhelp_basename = 'BackInTimeDevDoc'

# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  ('index', 'BackInTime.tex', 'Back In Time Development Documentation',
   'Germar Reitze', 'manual'),
]

# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'backintime', 'Back In Time Development Documentation',
     ['Germar Reitze'], 1)
]

# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'BackInTime', 'Back In Time Development Documentation',
   'Germar Reitze', 'BackInTime', 'One line description of project.',
   'Miscellaneous'),
]
