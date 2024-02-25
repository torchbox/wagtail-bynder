# Wagtail Bynder Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [unreleased]

## [0.2] - 2024-02-25

### Added

- Option to limit timeframes (to day, hours or minutes) in the sync management commands. [#10](https://github.com/torchbox/wagtail-bynder/pull/10) @ababic
- Setting to conditionally sync video data when chosen [#12](https://github.com/torchbox/wagtail-bynder/pull/12) @ababic
  The new setting is `BYNDER_SYNC_EXISTING_VIDEOS_ON_CHOOSE`, in line with those for images/documents.
- Improved test coverage

### Fixed

- Date filter silently ignored by Bynder in management commands [#10](https://github.com/torchbox/wagtail-bynder/pull/10) @ababic

## [0.1] - 2024-01-21

Initial release


[unreleased]: https://github.com/torchbox/wagtail-bynder/compare/v0.2 ...HEAD
[0.1]: https://github.com/torchbox/wagtail-bynder/compare/v.0.1...v0.2
[0.1]: https://github.com/torchbox/wagtail-bynder/compare/769e7b...v0.1
