# Convenience targets. Each one is also a plain command documented in the README.
PY ?= python3

.PHONY: help install test test-python test-firmware cad cad-fast renders diagrams bom wiring docs-gen site release check-links clean

help:
	@echo "install test test-python test-firmware cad cad-fast renders diagrams bom wiring docs-gen site release check-links clean"

install:
	$(PY) -m pip install -e ".[dev]"

test: test-python test-firmware

test-python:
	$(PY) -m pytest

test-firmware:
	$(MAKE) -C tests/firmware

cad:
	$(PY) tools/build_cad.py

cad-fast:
	$(PY) tools/build_cad.py --fast

renders:
	$(PY) tools/render_cad.py

diagrams:
	bash tools/build_diagrams.sh

bom:
	$(PY) tools/build_bom.py

wiring:
	$(PY) tools/build_wiring.py
	$(PY) tools/build_schematic.py

docs-gen: bom wiring
	$(PY) tools/build_module_docs.py
	$(PY) tools/build_site_data.py

site: docs-gen
	cd website && npm ci && npm run build

release:
	$(PY) tools/make_release.py

check-links:
	$(PY) tools/check_links.py

clean:
	$(MAKE) -C tests/firmware clean
	rm -rf releases/dist website/dist .pytest_cache
