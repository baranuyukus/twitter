# Release and GitHub

## Repository

The project was initialized as a Git repository and pushed to:

```text
https://github.com/baranuyukus/twitter.git
```

Current default branch:

```text
main
```

Initial release tag:

```text
v0.1.0
```

## GitHub Actions

The release workflow is stored at:

```text
.github/workflows/release.yml
```

It runs for:

- **Git tag push only** — pushing to `main` alone does **not** create a release.
- version tags like `v0.1.0` or `v0.1.1`
- manual workflow dispatch (Actions → Release → Run workflow, enter tag name)

### Create a release after code changes

```bash
# 1) Commit and push main (already done)
git push origin main

# 2) Create and push a new tag (required to trigger the workflow)
git tag v0.1.1
git push origin v0.1.1
```

Each release needs a **new** tag. Re-pushing an existing tag does not rebuild unless the tag is deleted first.

## Build Matrix

The workflow builds:

- macOS
- Windows

Each job:

1. Checks out the repository.
2. Installs Node.
3. Installs Python.
4. Runs `npm ci`.
5. Installs Python dependencies and PyInstaller.
6. Runs `npm run check`.
7. Builds Python bridge binaries.
8. Builds Electron packages.
9. Uploads artifacts.

For tag builds, the final job publishes a GitHub Release.

## Packaging

Electron Builder is configured in `package.json`.

The app package contains:

- Electron UI packed with ASAR.
- PyInstaller binaries copied to `resources/bin`.

Packaged resources include:

```text
app.asar
bin/ui_api
bin/ui_live
```

## Local Verification

The following checks were run locally:

```bash
npm run check
env/bin/python -m PyInstaller --clean --onefile --distpath py-dist --workpath py-build --name ui_api ui_api.py
env/bin/python -m PyInstaller --clean --onefile --distpath py-dist --workpath py-build --name ui_live ui_live.py
npx electron-builder --dir --publish never
```

## Git Ignore Policy

The repository excludes:

- credentials
- account files
- proxy files
- logs
- local config
- build outputs
- local virtual environments
- unrelated local experiments

