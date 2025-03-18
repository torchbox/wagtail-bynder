# Wagtail Bynder Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- Support for Wagtail 6.4

### Changed

- Image chooser tests now include new `default_alt_text` property

## Removed

- Wagtail versions (6.0-6.2) from tox testing matrix

## [0.7] - 2025-01-15

### Added

- Test against Wagtail 6.2 ([#35](https://github.com/torchbox/wagtail-bynder/pull/36)) @nickmoreton
- Add support for Wagtail 6.3 ([#35](https://github.com/torchbox/wagtail-bynder/pull/35)) @nickmoreton

### Changed

- Optimisation: Only initialise view classes in `PatchWagtailURLsMiddleware` when we know they are being used as a replacement ([#36](https://github.com/torchbox/wagtail-bynder/pull/36)) @ababic

## [0.6] - 2024-07-29

### Added

- BYNDER_MAX_DOCUMENT_FILE_SIZE and BYNDER_MAX_IMAGE_FILE_SIZE settings to guard against memory spikes when downloading asset files ([#31]https://github.com/torchbox/wagtail-bynder/pull/31) @ababic
- Automatic reformatting and downsizing of source images ([#32](https://github.com/torchbox/wagtail-bynder/pull/32)) @ababic
- Improved clash detection/handling in choosen views ([#30](https://github.com/torchbox/wagtail-bynder/pull/30)) @ababic

## [0.5.1] - 2024-07-29

### Fixed

- Video chooser URL generation @ababic

## [0.5] - 2024-07-29

### Fixed

- Compatibility with Wagtail 6.1 ([#34](https://github.com/torchbox/wagtail-bynder/pull/34)) @ababic

## [0.4.1] - 2024-07-02

### Fixed

- Allow `RedirectToBynderMixin` views to process post requests as normal when not redirecting to Bynder ([#28](https://github.com/torchbox/wagtail-bynder/pull/28)) @ababic

## [0.4] - 2024-04-25

### Changed

- Dropped support for Wagtail < 5.2, Django < 4.2 - in line with currently maintained versions. @zerolab
- Tidied up the tooling configuration and dependencies. @zerolab
- Stale renditions are now deleted when file or focal area changes are detected. [#24](https://github.com/torchbox/wagtail-bynder/pull/24) @ababic
- Improve conversion of focus points into focal areas [#26](https://github.com/torchbox/wagtail-bynder/pull/26) @ababic
  Now the focal area is square at 40% the width/height of the image with a center in the focus point.

### Fixed

- Fix: `TypeError` when using new 'refresh' commands [#23](https://github.com/torchbox/wagtail-bynder/pull/23) @ababic

## [0.3] - 2024-04-12

### Added

- Added `source_filename` and `original_filesize` fields to all base models, and updated `update_from_asset_data()` to set them accordingly.
- Added `original_height` and `original_width` fields to image and video base models, and updated `update_from_asset_data()` to set them accordingly.
- Added "What to ask of Bynder" section to `README.md`. [#15](https://github.com/torchbox/wagtail-bynder/pull/15) @ababic
- Improved test coverage
- Management commands to refresh all local objects. [#18](https://github.com/torchbox/wagtail-bynder/pull/18) @ababic
  They are `refresh_bynder_documents`, `refresh_bynder_images` and `refresh_bynder_videos`

### Removed

- Removed the `metadata` field from all base models, along with `directly_mapped_bynder_fields` attributes, and the `extract_relevant_metadata()` method used for setting the field value during an update.
- Removed the `bynder_original_filename` field from all base models. This has now been succeeded by `source_filename`, which stores a value more relevant to each type.
- Removed the `bynder_id_hash` field from all base models.
- Removed the `download_asset_file()` method from all base models. The responsibility for downloading assets now falls to the `update_file()` method (applies to image and document models only).

### Changed

- The `bynder_id` field on all base models now supports `null` values, allowing a mix of images/documents from different sources to be added to be saved.
- Fixed an issue with `file_hash` and `file_size` fields not being set correctly when a model instance is created or updated to reflect Bynder asset data.
- Updated `asset_file_has_changed()` implementations on all models to take into account values from new `source_filename`, `original_filesize`, `original_height` and `original_width` model fields.
- Consistently raise `wagtail_bynder.exceptions.BynderAssetDataError` (instead of `django.core.exceptions.ImproperlyConfigured` or `KeyError`) when API representations from Bynder do not contain data required for the integration to work properly.
- Changed the default `BYNDER_VIDEO_PRIMARY_DERIVATIVE_NAME` setting value from `"Web-Primary"` to `"WebPrimary"` to reflect new guidance in `README.md`.
- Changed the default `BYNDER_VIDEO_FALLBACK_DERIVATIVE_NAME` setting value from `"Web-Fallback"` to `"WebFallback"` to reflect new guidance in `README.md`.
- Changed the default `BYNDER_IMAGE_SOURCE_THUMBNAIL_NAME` setting value from `"webimage"` to `"WagtailSource"` to reflect new guidance in `README.md`.

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

[unreleased]: https://github.com/torchbox/wagtail-bynder/compare/v0.5...HEAD
[0.6]: https://github.com/torchbox/wagtail-bynder/compare/v.0.5.1...v0.6
[0.5.1]: https://github.com/torchbox/wagtail-bynder/compare/v.0.5...v0.5.1
[0.5]: https://github.com/torchbox/wagtail-bynder/compare/v.0.4...v0.5
[0.4.1]: https://github.com/torchbox/wagtail-bynder/compare/v.0.4...v0.4.1
[0.4]: https://github.com/torchbox/wagtail-bynder/compare/v.0.3...v0.4
[0.3]: https://github.com/torchbox/wagtail-bynder/compare/v.0.2...v0.3
[0.2]: https://github.com/torchbox/wagtail-bynder/compare/v.0.1...v0.2
[0.1]: https://github.com/torchbox/wagtail-bynder/compare/769e7b...v0.1
