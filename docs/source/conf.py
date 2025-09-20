# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "chatterflow"
copyright = "2025, Ishan Bhat"
author = "Ishan Bhat"
release = "0.0.1"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinxdoc"
# html_static_path = ['_static']
extensions = [
    "sphinx.ext.autodoc",  # generate docs from docstrings
    "sphinx.ext.napoleon",  # support Google/NumPy style docstrings
    "sphinx.ext.viewcode",  # add links to highlighted source code
]
