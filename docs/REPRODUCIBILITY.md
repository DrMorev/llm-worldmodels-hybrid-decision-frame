# Reproducibility and evidence inspection

This document separates ordinary repository inspection from the historical full C-03 development execution.

## Implementation identity

The exact comparison

```bash
git diff \
  4225b49c6028ae5ddcc879eae1a9b9e6be2960d4 \
  2f7aa988cb0f607def899f789ba5f846cb4f21ba \
  -- development tests
```

is empty. The post-C-03 C-04 changes did not modify `development/**` or `tests/**`. `2f7aa988cb0f607def899f789ba5f846cb4f21ba`, the R-01 base, retains the C-03 implementation and test surface. The R-01 diff changes no `development/**` or `tests/**` path, so the release candidate retains that same implementation and test surface.

This identity statement does not make C-03 confirmatory evidence and does not authorize a rerun.

## Historical C-03 execution

Historical command:

```bash
python -B -m development.statistical_feasibility.run \
  --stage2-primary-map \
  --workers 4 \
  --output-dir <OUTPUT_DIR>
```

Historical execution environment:

* Python: `3.11.15`;
* workers: `4`;
* observed wall time: approximately 3 h 27 min.

The runtime is historical evidence from its execution environment, not a performance promise for another operating system, Python build, processor, or storage device.

The full C-03 run is expensive and is not required for ordinary inspection. It must not be substituted for the bounded smoke command during routine release verification.

## Public inspection commands

R-01 validated the following commands under Python `3.14.6`:

```bash
python -B -m unittest discover -s tests -v
python -B -m compileall development tests
python -B -m development.statistical_feasibility.run --smoke
```

The unit-test command is the lightweight ordinary inspection path. The `--smoke` command is optional and not lightweight: under Python `3.14.6`, it took approximately 8.5 minutes and wrote approximately 1.36 GB of temporary output during R-01 validation. These observed figures are not runtime or storage guarantees. The smoke runner creates its output in an OS temporary directory when `--output-dir` is omitted. It does not place generated scientific evidence in the Git working tree.

These commands test the public implementation surface. They do not reproduce the full 2,400-population C-03 execution and do not create a confirmatory result.

## C-03 evidence object

The intended immutable evidence object is the complete unchanged C-03 ZIP.

SHA-256:

`28021bfb5c095cc2a8424fb0f21300f15aa34e4c49bdbd467ff91e2d4a276610`

The C-03 evidence object is archived on Zenodo at [https://zenodo.org/records/22081466](https://zenodo.org/records/22081466). Its version-specific DOI is [https://doi.org/10.5281/zenodo.22081466](https://doi.org/10.5281/zenodo.22081466); its all-versions DOI is [https://doi.org/10.5281/zenodo.22081465](https://doi.org/10.5281/zenodo.22081465). For exact C-03 evidence verification, use the version-specific DOI or record and verify the downloaded file against the canonical SHA-256. No GitHub release URL or release tag is asserted.

The release-facing result note lists the component artifact hashes: [C03_RESULT.md](C03_RESULT.md).

## SHA-256 verification

On systems with `sha256sum`:

```bash
sha256sum <PATH_TO_C03_ZIP>
```

Expected digest:

```text
28021bfb5c095cc2a8424fb0f21300f15aa34e4c49bdbd467ff91e2d4a276610
```

On Windows PowerShell:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath <PATH_TO_C03_ZIP>
```

The computed value must match the expected digest before the archive is treated as the C-03 evidence object.

## External requirements

The scientific implementation requires no:

* network service;
* proprietary model;
* private data;
* OCR system;
* external API.

The repository implementation and tests use the Python standard library. External archival publication is a release operation and is distinct from scientific execution.
