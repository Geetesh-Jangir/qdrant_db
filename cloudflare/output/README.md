# Output (local mirror)

When you run the Worker with R2, artifacts are stored in the bucket (see root `README.md`).

After `wrangler r2 object get`, you can place copies here:

- `scraped_articles.json` — successful extractions
- `scrape_errors.json` — failures with structured error codes and messages
