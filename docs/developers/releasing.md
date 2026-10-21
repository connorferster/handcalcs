# Releasing

## Checklist

1. **Tests pass** on the release branch: `uv run pytest`, and CI is green on all
   platforms.
2. **Golden files** are current and reviewed (see [Tests](testing.md#golden-files)).
3. **Version**: update `version` in `pyproject.toml` (the package is built with
   [flit](https://flit.pypa.io/)).
4. **Docs**: in `docs/conf.py`, set the default `HC_SOURCE_REF` to the release tag (for
   example `"v2.0.0"`) so source links in the published docs point at the released
   code. Build with `-W` to catch broken links and references.
5. **Changelog**: add the release to [the changelog](../reference/changelog.md).
6. **Tag and release** on GitHub, with the tag `v` + the version (`v2.0.0`).
   Publishing a GitHub release runs the `python-publish.yml` workflow, which builds
   the wheel and sdist (`uv build`, flit backend), checks the version matches the tag
   and uploads to PyPI.
7. After the release, set `HC_SOURCE_REF` back to the development branch.

## CI

| Workflow | Runs |
|---|---|
| `.github/workflows/python-pytest.yml` | On pushes and pull requests to `main`: `uv sync`, `black --check`, `pytest`, on Linux, macOS and Windows with Python 3.11 to 3.14. |
| `.github/workflows/python-publish.yml` | On a published GitHub release: build, check the version against the tag and upload to PyPI. |

## PyPI trusted publishing

The publish workflow has no API token: PyPI trusts it directly. This is set up once, on
[pypi.org](https://pypi.org/manage/project/handcalcs/settings/publishing/), under
**Publishing → Add a new publisher → GitHub**:

| Field | Value |
|---|---|
| Owner | `connorferster` |
| Repository | `handcalcs` |
| Workflow | `python-publish.yml` |
| Environment | `pypi` |

The `pypi` environment exists in the repository's **Settings → Environments** (GitHub
creates it on the first run if it doesn't); a required reviewer on it makes each upload
wait for approval.

