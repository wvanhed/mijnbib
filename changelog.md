# Changelog

new: new feature /  impr: improvement /  fix: bug fix

## v0.7.2 - 2025-01-31

- fix: remove pip dependency added to v0.7.1

## v0.7.1 - 2025-01-31

- fix: support both old and new extend loan UI, to return extend loan info

## v0.7.0 - 2025-01-25

- impr: [breaking] re-add support for optional city parameter;
        when used might return extra loan extension information
- fix: IncompatibleSourceError on changed user interface for extending loan

## v0.6.0 - 2024-07-05

- impr: [breaking] remove support for city parameter
- impr: various improvements (documentation, linting, black->ruff, refactoring)

## v0.5.6 - 2024-03-09

- fix: broken login (oauth)

## v0.5.5 - 2024-03-05

- fix: broken login (form) because of change at site.
  Note: alternative oauth login still broken.
- impr: raise TemporarySiteError at oauth login when 5xx (part 3)

## v0.5.4 - 2024-02-21

- impr: improve extensibility of oauth login handler

## v0.5.3 - 2024-02-13

- impr: error handling during login now can raise TemporarySiteError

## v0.5.2 - 2024-02-11

- impr: error handling for non-existing account id

## v0.5.1 - 2024-01-11

- impr: extra logging info for login validation warning

## v0.5.0 - 2024-01-07

- impr: speed up form and oauth login calls
- impr: add timeout for all URL calls
- impr: set user-agent for all URL calls
- impr: code cleanup & refactoring

## v0.4.0 - 2024-01-02

- new: experimental login via OAuth (optional)
- new: city parameter to create MijnBibliotheek object is now optional
- impr: set some log messages at INFO level, and improve log level printing

## v0.3.0 - 2023-12-27

- new: rename base exception to MijnbibError
- impr: general internal improvements

## v0.2.0 - 2023-12-20

- new: Add extend_by_ids method
- new: Add 'Makefile all' target
- impr: refactor file organization
- impr: error handling (including rename and cleanup of custom errors)

## v0.1.0 - 2023-12-17

- new: Add 'Makefile publish' target
- new: Use mijnbib.ini file for storing credentials
- impr: Add account id to loan class
- impr: Documentation improvements

## v0.0.1 - 2023-12-08

- Initial version
