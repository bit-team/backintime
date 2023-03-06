# How to contribute to _Back In Time_

*Thanks for taking the time to contribute!*

The maintenance team will welcome all types of contributions. No contribution
will be rejected just because it doesn't fit to our quality standards,
guidelines or rules. Every contribution is reviewed and if needed will be
improved together with the maintainers.

Please always make a new branch when preparing a Pull Request or a patch.
Baseline that feature or bug fix branch on `dev` (the latest development
state). When open a pull request please make sure that it targets
`bit-team:dev`.

Please take the following best practices into account if possible (to reduce
	the work load of the maintainers and to increase the chance that your pull
	request is accepted):
 - Follow [PEP 8](https://peps.python.org/pep-0008/) as a minimal Style Guide
   for Python Code
 - Follow [Google Style Guide](https://sphinxcontrib-napoleon.readthedocs.org/en/latest/example_google.html) for
   docstrings (see our own [HOWTO about doc generation](common/doc-dev/1_doc_maintenance_howto.md)).
 - Be careful when using automatic formatters like `black` and please mention
   the use of it when opening a pull request.
 - Run unit tests before you open a Pull Request. You can run them via
   `make`-system with `cd common && ./configure && make && make test` or you
   can use `pytest`.
 - Try to create new unit tests if appropriated. Use Pythons regular `unittest`
   instead of `pytest`. If you know the difference please try follow the
   _Classical (aka Detroit) school_ instead of _London (aka mockist) school_.

## Resources

 - [Mailing list _bit-dev_](https://mail.python.org/mailman3/lists/bit-dev.python.org/) for development related topics
 - [Source code documentation for developers](https://backintime-dev.readthedocs.org)
 - [Translations](https://translations.launchpad.net/backintime) are done on a separate platform
 
## Licensing of contributed material
Keep in mind as you contribute, that code, docs and other material submitted
to the project are considered licensed under the same terms (see
[LICENSE](LICENSE)) as the rest of the work.

## Further reading
- https://www.contribution-guide.org
- https://mozillascience.github.io/working-open-workshop/contributing

<sub>March 2023</sub>
