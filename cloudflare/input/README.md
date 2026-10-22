# Input: failed scrape URLs from Lightsail

Upload your pipeline failure ledger here before syncing to R2 (see `../README.md`).

Typical files (copy from Lightsail):

- `news_failures/source.json` — full persistent ledger (recommended input)
- `failed_source.json` — per-run or daily slice (`items` array, same shape)

The Worker expects JSON: `{ "items": [ { "url", "title", "snippet", ... } ] }`.
