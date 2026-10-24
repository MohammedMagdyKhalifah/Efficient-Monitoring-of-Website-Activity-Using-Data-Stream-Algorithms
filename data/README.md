# Dataset provenance

NASA Kennedy Space Center WWW HTTP access logs, July 1995 capture.

- Publisher: Internet Traffic Archive.
- Description: https://ita.ee.lbl.gov/html/contrib/NASA-HTTP.html
- Original download: https://ita.ee.lbl.gov/traces/NASA_access_log_Jul95.gz
- Collected by Jim Dumoulin; contributed by Martin Arlitt and Carey Williamson.
- The archive explicitly permits free redistribution and requests analysis of general traffic patterns only.
- The original compressed file is included unchanged. No synthetic events are added.
- `manifest.json` records SHA-256, observed counts, actual dates, statuses and examples.

The archive description refers to July 1-31. The actual included capture contains
1,891,714 valid requests from July 1 to July 28 at 13:32:25 (-0400), followed by
one incomplete raw line (`alyssa.p`). The parser rejects that fragment. All valid
requests are preserved in source order, including duplicate requests and errors.
Reading through gzip EOF verifies its integrity; partial-month coverage is a
property of this source, not evidence of zero traffic afterward.

`-` response byte counts become `None`; these records remain usable because the
three algorithms do not use byte counts. A host string identifies an originating
host, not an authenticated user or a unique person.
