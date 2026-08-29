# public-apis discovery catalog

Omni treats `public-apis/public-apis` as a community/manual-curation discovery source. It reads the
`master` branch's `README.md` through the fixed GitHub Contents API endpoint with
`Accept: application/vnd.github+json`, validates the file envelope, strictly decodes bounded
base64 as UTF-8, and records the GitHub blob SHA as catalog revision.
The source permits 1 outbound request per minute/process and `max_attempts=1`, so transient
failures never trigger an immediate second GitHub request. Cache hits consume no outbound quota.

Only category tables with columns `API | Description | Auth | HTTPS | CORS` are parsed. Marketing,
index, badge, sponsor, and unrelated tables are ignored. Documentation URLs and HTTPS/auth/CORS
columns remain unverified display hints. `download_url`, `html_url`, and `git_url` are never
followed.

The repository's MIT license covers that repository; it does not grant rights to use the external
services it lists. Underlying API terms, commercial rights, privacy, and security require separate
human review.
