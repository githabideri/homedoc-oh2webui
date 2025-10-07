# Changelog

All notable changes to this project will be documented here. Dates use UTC.

## [0.2.1] - 2025-10-06
- Distilled session transcripts now suppress bootstrap prompts, strip metadata noise, and keep a single succinct message per step.
- Regenerated artifacts via the CLI with the project virtualenv to validate the end-to-end distill → upload → chat flow.
- Updated documentation, tests, and version metadata for the refreshed pipeline.

## [0.2.0] - 2025-10-06
- Added optional chat export capture controlled by `OH2WEBUI_CAPTURE_CHAT_EXPORT` / `OH2WEBUI_DEBUG`, writing JSON transcripts that match Open WebUI’s manual download format.
- Extended CLI `chat` command output to surface the saved export path.
- Documented end-to-end automation workflow and new environment variables.
- Updated tests to cover export capture behavior and JSON structure.

## [0.1.0] - 2025-10-06
- Initial release with extract → distill → package → upload → chat pipeline integration.
