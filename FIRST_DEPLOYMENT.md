# First Deployment

1. Fork/clone repository.
2. Enable GitHub Actions in repository settings.
3. Enable GitHub Pages with **Build and deployment: GitHub Actions**.
4. (Optional) Configure branch protection for `main`.
5. Push to default branch and run **Deploy Pages** workflow once.
6. Run **Scheduled Ingestion** workflow manually once.
7. Verify `status/system-status.json` and `reports/system-health.json` were generated.
8. Verify Pages site loads and displays automation status.
9. Confirm scheduled workflows are enabled.

If scheduled workflows are auto-disabled by GitHub inactivity (public repo), re-enable from the Actions tab and trigger **Scheduled Ingestion** manually.
