# Changelog

new: new feature /  impr: improvement /  fix: bug fix

## v0.5.5 - 2024-03-05

- fix: broken login (form) because of change at site. 
  Note: alternative oauth login still broken.

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
