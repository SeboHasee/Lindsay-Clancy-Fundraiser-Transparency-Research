# Disaster Recovery

## Deleted dataset files
- Restore from Git history (`git checkout <commit> -- data reports status`).
- Re-run: `python -m research validate && python -m research analyze && python -m research report`.

## Corrupted data
- Revert to last known-good commit.
- Re-run scheduled ingestion manually and inspect review queue.

## Broken deployment
- Run `Deploy Pages` workflow manually.
- If still failing, restore prior known-good commit and redeploy.

## Failed migration
- Keep previous SQLite file backup from Git-tracked JSON canonical data.
- Reinitialize with `python -m research setup` and replay canonical JSON.

## Broken source parser
- Source adapter errors are review-queued and status degrades.
- Patch adapter in `src/sources/`, add tests, rerun ingestion.

## Compromised credential
- Revoke/rotate repository secrets.
- Audit recent Actions runs and open security issue.

## Accidental bad commit
- Revert via PR.
- Regenerate reports and status artifacts.
