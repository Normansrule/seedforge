# Releases

Release bundles are **attached to GitHub Releases**, not committed. Build them locally with:

```bash
python tools/make_release.py            # version from software/seedforge/__init__.py
```

which writes to `releases/dist/` (git-ignored):

| file | content |
|---|---|
| `SeedForge_v0.3.0-alpha_COMPLETE.zip` | the whole repository at the tagged commit (without `node_modules`, caches, generated synthetic images) |
| `SeedForge_v0.3.0-alpha_PHASE1_PRINTS.zip` | 3MF + STL + STEP of the Phase-1 core-cell parts, the fit coupon and the Phase-2 M3 parts, with a print list |
| `SeedForge_v0.3.0-alpha_SEED_REFERENCE_CAD.zip` | MR/PR reference models (STEP, STL, 3MF, GLB) with the geometry notes |
| `SeedForge_v0.3.0-alpha_DOCUMENTATION.zip` | Markdown docs, renders, diagrams and the built website (static HTML) |
| `SHA256SUMS.txt` | checksums |

`RELEASE_NOTES.md` is the release body. The `release.yml` workflow builds the same files when a `v*` tag is pushed and attaches them to the
GitHub Release.

Versioning: semantic versions with pre-release tags (`v0.3.0-alpha`); engineering revisions (R3.1)
are noted in the changelog. No 1.0 before physical validation justifies it.
