# ha-ecohome

This is a Home Assistant integration for the [New Energy
Eco-Home](https://ehome.ne01.com/) heat pump API, which is used (among others)
by Batavia Heat heat pumps in the Netherlands.

## Installation

You can install this repo via HACS or by copying the integration files yourself.
I'd recommend using HACS.

### Installation via HACS

First, install HACS using these instructions: https://hacs.xyz/docs/use/download/download/

Then, activate HACS using these instructions: https://hacs.xyz/docs/use/configuration/basic/

Then, on the HACS dashboard under the three dots (top right) you can add this
repository as a custom repository:

- Repository: https://github.com/sgielen/ha-ecohome
- Type: Integration

Now, click Add. After this, you can search for Eco-Home, and download and install
from there.

The repository is awaiting review to be searchable directly from within HACS.

### Installing yourself

Alternatively, you can copy the `custom_components/ecohome` directory from this
repository directly into your `config/custom_components` directory inside Home
Assistant.

### Configuration

After installation, you can add the integration inside Home Assistant settings
-> Devices and Services, search for Eco-Home.  This requires your username and
password. If you have only one device, it is immediately added; if you have
multiple you can select which ones to add.  Devices shared with you cannot be
added yet, but this is probably an easy fix.

## Development

### Running tests

This project uses `uv` for dependency management and `pytest` for testing.

- Install dependencies: `uv sync`
- Run the test suite: `uv run pytest`

### Releases

- Update version number in `pyproject.toml` and
  `custom_components/ecohome/manifest.json`. I try to keep the version
  number in sync with the Python `ecohome` library if possible.
- Run `uv sync`, commit and push all changes
- Create a tag and github release: `gh release create v0.1.2 --title "v0.1.2" --generate-notes`
- The new version should be indexed by HACS automatically.
