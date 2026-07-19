PYTHON ?= py -3.11
VENV_PYTHON ?= .tso/Scripts/python.exe
VENV_CONFIG ?= .tso/pyvenv.cfg
DATA_DIR ?= ../public_spine_data

.PHONY: help setup-venv install-deps install-test-deps install-visualise test validate

help:
	@echo "make setup-venv   Create the Python 3.11 virtual environment"
	@echo "make install-deps Install pinned build/acquisition dependencies"
	@echo "make install-test-deps Install pinned test extras"
	@echo "make install-visualise Install optional notebook/plotting extras"
	@echo "make test         Run the full automated test suite"
	@echo "make validate     Validate DATA_DIR (default ../public_spine_data)"
	@echo "On Unix, override PYTHON=python3 VENV_PYTHON=.tso/bin/python"

setup-venv: $(VENV_CONFIG)

$(VENV_CONFIG):
	$(PYTHON) -m venv .tso

install-deps: $(VENV_CONFIG)
	"$(VENV_PYTHON)" -m pip install --upgrade pip
	"$(VENV_PYTHON)" -m pip install -r requirements.txt

install-test-deps: $(VENV_CONFIG)
	"$(VENV_PYTHON)" -m pip install -r test-requirements.txt

install-visualise: $(VENV_CONFIG)
	"$(VENV_PYTHON)" -m pip install -r requirements-visualise.txt

test:
	"$(VENV_PYTHON)" -m pytest

validate:
	"$(VENV_PYTHON)" cli.py validate-release "$(DATA_DIR)"
