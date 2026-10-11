# Repository size and large files

Decision: **no Git LFS** for v0.3.0-alpha.

* The largest single file is a few megabytes (a GLB viewer model or STL); everything is well below
  GitHub's 50 MB warning and 100 MB limit.
* GitHub Pages cannot serve LFS objects from the deployed site. The website's models must be
  ordinary static files, so `website/public/models/` holds optimised GLB copies.
* All CAD exports are reproducible from source (`python tools/build_cad.py`), so they are committed
  for convenience, not as the only copy of the design.
* Release bundles (complete package, Phase-1 print pack, seed-reference CAD) are attached to GitHub
  Releases, not committed.
* The synthetic vision set (about 23 MB) is not committed; `python -m seedforge.vision demo`
  regenerates it deterministically. Only its report and three example overlays are in the repository.

Revisit this if real image datasets or photographs grow past a few hundred megabytes; then store
them in a release asset or an external dataset host and keep a manifest with checksums here.

Check sizes with:

```bash
git count-objects -vH
find . -path ./website/node_modules -prune -o -type f -size +5M -print
```
