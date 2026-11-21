# 06. testing — cases, known issues, acceptance

- `test_cases.csv` — header: `id,area,case,method,expected,last_result,evidence`.
  One row per distinct check; evidence points at the artifact that proves it.
- `known_issues.md` — accepted limitations (e.g. strings that can't be baked
  natively), each with why-it's-accepted and where it's tracked.
- `acceptance_report.md` — the §14-style run: every check, real data, pass/fail.

**Rule:** tests assert only verified facts — if a claim isn't cheaply checkable,
verify it once forensically, then assert exactly what's true (including
negative assertions). A test asserting an unverified fact will rot.
