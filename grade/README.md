# Per-level grade archives

AutoZuma creates one append-only CSV for each completed campaign level in this
directory, for example `1-1.csv`.

Source screenshots are stored under `screenshots/<level>/`. OCR failures that
reach the retry limit are stored under `failed/`. Generated CSV, screenshot, and
failure files are intentionally ignored by Git; this README keeps the archive
directory present in a fresh checkout.

GAME OVER attempts use independent per-level tables under `gameover/`, for
example `gameover/10-1.csv`, with source images under
`gameover/screenshots/10-1/`.

CSV rows contain only values recognized from the result screen. Timestamps,
internal map identifiers, screenshot paths, OCR diagnostics, and runtime
parameter snapshots are deliberately excluded. The level is represented by the
CSV filename itself.
