# 07. releases — one record per release

Per release: `<name>.md` + `<name>.sha256.txt` (checksum manifest of the whole
shipped tree).

The record carries: supported source version, coverage summary (from the
catalog), SHA256 manifest, known issues, and repro steps (clean install +
patcher → expected result). The shipped artifact is a build directory or patch
package — **never** committed to git; only its hashes.
