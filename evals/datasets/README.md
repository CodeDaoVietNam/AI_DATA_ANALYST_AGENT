# Eval Datasets

This folder stores local evaluation snapshots referenced by `evals/manifest.json`.

Large raw datasets are intentionally ignored by git. Use:

```bash
PYTHONPATH=. python evals/download_datasets.py
```

The downloader will:

- create CSV snapshots from local files in `data/raw`
- auto-download datasets only when a stable direct URL is configured
- print manual placement instructions for Maven/Kaggle-style datasets that require browser download

After placing raw external dataset packages in this folder, normalize them into manifest-ready
single-file CSV snapshots:

```bash
PYTHONPATH=. python evals/prepare_snapshots.py
```

Strict U5 eval expects all 20 manifest datasets to exist:

```bash
PYTHONPATH=. python evals/prepare_snapshots.py
PYTHONPATH=. python evals/download_datasets.py --validate
PYTHONPATH=. python evals/run_eval.py --strict
```
