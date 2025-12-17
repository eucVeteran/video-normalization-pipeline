VENV := venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip

# For Windows use
# PYTHON := $(VENV)/Scripts/python

.PHONY: all setup run clean help

all: setup run verify

setup:
	@echo "--- ⚙️ Setting up environment ---"
	python3 -m venv $(VENV)
	@echo "Environment created."
# $(PIP) install -r requirements.txt
# if we had requirements

run:
	@echo "--- 🎬 Starting Batch Processing ---"
	@mkdir -p outputs
	$(PYTHON) src/main.py inputs outputs
	@echo "--- ✨ All Done! Check /outputs folder ---"

verify:
	@echo "--- 🔍 Verifying Outputs ---"
	$(PYTHON) src/verify.py

clean:
	@echo "Cleaning up..."
	rm -rf outputs/*
	rm -rf $(VENV)
	@echo "Cleaned."

help:
	@echo "Available commands:"
	@echo "  make setup   - Create virtual environment"
	@echo "  make run     - Process all videos in inputs/"
	@echo "  make verify  - Verify output videos"
	@echo "  make clean   - Remove outputs and venv"
	@echo "  make all     - Setup + Run (Default)"