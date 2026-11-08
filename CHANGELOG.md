# Changelog

## [1.1.3](https://github.com/udondan/lanis/compare/v1.1.2...v1.1.3) (2026-11-06)


### Bug Fixes

* read the substitution plan of accounts without access to the whole plan ([#75](https://github.com/udondan/lanis/issues/75)) ([0d930f8](https://github.com/udondan/lanis/commit/0d930f8b94e6c09d4b0bed0ecc9457384d458542))

## [1.1.2](https://github.com/udondan/lanis/compare/v1.1.1...v1.1.2) (2026-11-02)


### Dependencies

* **deps:** update python docker tag to v3.15 ([#65](https://github.com/udondan/lanis/issues/65)) ([fef07fd](https://github.com/udondan/lanis/commit/fef07fd75aa40fef8ee28a293392e92462ccb813))

## [1.1.1](https://github.com/udondan/lanis/compare/v1.1.0...v1.1.1) (2026-10-29)


### Bug Fixes

* remove pip from the Docker image ([#53](https://github.com/udondan/lanis/issues/53)) ([2a9fa7a](https://github.com/udondan/lanis/commit/2a9fa7a71510f0126bd9295e583007072bfeb9a8))

## [1.1.0](https://github.com/udondan/pylanis/compare/v1.0.0...v1.1.0) (2026-10-29)


### Features

* publish the Docker image udondan/lanis to Docker Hub ([#50](https://github.com/udondan/pylanis/issues/50)) ([49612f2](https://github.com/udondan/pylanis/commit/49612f2861e0f1d0ebb313d8ce57c6afad8a9267))

## [1.0.0](https://github.com/udondan/pylanis/compare/v0.2.1...v1.0.0) (2026-10-29)


### ⚠ BREAKING CHANGES

* add Python SDK and lanis CLI alongside the MCP server ([#46](https://github.com/udondan/pylanis/issues/46))

### Features

* add Python SDK and lanis CLI alongside the MCP server ([#46](https://github.com/udondan/pylanis/issues/46)) ([836d48f](https://github.com/udondan/pylanis/commit/836d48fcc1e3d417dec7055e61aefd6ce4975bf0))

## [0.2.1](https://github.com/udondan/pylanis/compare/v0.2.0...v0.2.1) (2026-10-29)


### Bug Fixes

* build the Docker image again ([#45](https://github.com/udondan/pylanis/issues/45)) ([fa8cef0](https://github.com/udondan/pylanis/commit/fa8cef015a4168d867bf68bab16ddf6bc4552f1a))
* log in again when the Lanis session ends ([#43](https://github.com/udondan/pylanis/issues/43)) ([928c70f](https://github.com/udondan/pylanis/commit/928c70f7c31259ed882b658854f68d8a006381ed))
* never reuse the stored session of another account ([928c70f](https://github.com/udondan/pylanis/commit/928c70f7c31259ed882b658854f68d8a006381ed))
* return all conversations when there are fewer than requested ([928c70f](https://github.com/udondan/pylanis/commit/928c70f7c31259ed882b658854f68d8a006381ed))

## [0.2.0](https://github.com/udondan/pylanis/compare/v0.1.0...v0.2.0) (2026-10-29)


### Features

* add dev optional dependencies for pytest, pytest-asyncio, and anyio ([ec92f9f](https://github.com/udondan/pylanis/commit/ec92f9f8de0d491d48419008773fb0912420759e))
* add GitHub Actions CI workflow for lint and test on pull requests ([b8debd0](https://github.com/udondan/pylanis/commit/b8debd0272cfa17aab43f7220043806b8803d211))
* add lanis_get_schools, lanis_get_folders, lanis_check_app_availability tools ([2c63d53](https://github.com/udondan/pylanis/commit/2c63d5343a10c7c6b3cf4fbdfa14df7eac274dc0))
* add lanis_get_schools, lanis_get_folders, lanis_check_app_availability tools ([04e5497](https://github.com/udondan/pylanis/commit/04e5497748f6d649d7c889411a17bfa8ee46d026))
* add MCP tools for Stundenplan, Lerngruppen, Dateispeicher, Dateiverteilung, and Wahlen ([29c56db](https://github.com/udondan/pylanis/commit/29c56dbf75cc986c617fb766d75923364263ed8d))
* add MCP tools for Stundenplan, Lerngruppen, Dateispeicher, Dateiverteilung, and Wahlen ([b105b85](https://github.com/udondan/pylanis/commit/b105b856bb9bc486ebec79ce7eb30090efa6768e))
* add mise config with tasks for setup, test, lint, format, server, build, and inspect ([04ca497](https://github.com/udondan/pylanis/commit/04ca4979828998c2766282a97b9785caa617731d))
* add MIT license ([8172b88](https://github.com/udondan/pylanis/commit/8172b886bff8962aa28b94fce71e85fba156f2fd))
* add MIT license ([102bdd6](https://github.com/udondan/pylanis/commit/102bdd6d59d5f7917948b0adc62216d7b566005a))
* add Renovate config for automated dependency updates ([65f911d](https://github.com/udondan/pylanis/commit/65f911dcfd2b49036df5981e6a1cd109bca10862))
* Adds Dockerfile to build image for Docker MCP Toolkit ([#13](https://github.com/udondan/pylanis/issues/13)) ([ce48fe4](https://github.com/udondan/pylanis/commit/ce48fe4ba79252e122089bf0a4ce68e896a8900d))
* initial MCP server for Schulportal Hessen (Lanis) ([de9bd30](https://github.com/udondan/pylanis/commit/de9bd30e6b00f80732483e2a6ea5a7dfc11f5262))


### Bug Fixes

* correct timetable day assignment and expose duration for multi-hour lessons ([#15](https://github.com/udondan/pylanis/issues/15)) ([f7244ae](https://github.com/udondan/pylanis/commit/f7244aee715cf81abf379e2a2416d2179976c9cb))
* **deps:** pin selectolax below 1.0 ([#29](https://github.com/udondan/pylanis/issues/29)) ([2277bbc](https://github.com/udondan/pylanis/commit/2277bbc7b83241cdb4152aa85b22db62abff6a8c))
* detect app availability by URL when school renames apps ([ac9a9c2](https://github.com/udondan/pylanis/commit/ac9a9c267a53fb9fcaa830d4951b9613d399d40c))
* detect app availability by URL when school renames apps ([6e3cefe](https://github.com/udondan/pylanis/commit/6e3cefe8de4c0491b5a1ee975f0a1a5484ab2b8a))
* patch lanisapi sid parsing bug and add integration tests ([67e0624](https://github.com/udondan/pylanis/commit/67e06243a1617583ea7a93043c2a0ea369303e3b))
* patch lanisapi sid parsing bug and add integration tests ([88ff6a7](https://github.com/udondan/pylanis/commit/88ff6a766ca108b69360c0720fa6de8ca35c5b24))
* pin mcp to 1.x and restore green CI ([#17](https://github.com/udondan/pylanis/issues/17)) ([57ee99b](https://github.com/udondan/pylanis/commit/57ee99ba95f8ccdf576d344f971e273e31f9bf67))
* remove lanis_ prefix from MCP tool names to avoid double-prefix ([181ef49](https://github.com/udondan/pylanis/commit/181ef494f7202c47b5ebefb781eb77a235170357))
* remove lanis_ prefix from MCP tool names to avoid double-prefix ([9dda2cb](https://github.com/udondan/pylanis/commit/9dda2cb673fa343b861f2836935f316d6f9cb8a2))
* report an unused Vertretungsplan instead of failing with a TypeError ([#39](https://github.com/udondan/pylanis/issues/39)) ([07af206](https://github.com/udondan/pylanis/commit/07af2063b2c282d01b38064cd518899e2dea6353))
* resolve LSP type errors and fix potential None sid cookie bug ([7b50f91](https://github.com/udondan/pylanis/commit/7b50f9106910b45b4c6b426fd58993fb4a673799))


### Dependencies

* **deps:** update dependency mcp to v2 ([#20](https://github.com/udondan/pylanis/issues/20)) ([4499935](https://github.com/udondan/pylanis/commit/4499935652e8e8fec04ae1b4e86be5eac0369c65))
* **deps:** update dependency mcp to v2.3.0 ([#26](https://github.com/udondan/pylanis/issues/26)) ([fe38161](https://github.com/udondan/pylanis/commit/fe3816132e7fc76bffad8c74914731d54bc16da7))
