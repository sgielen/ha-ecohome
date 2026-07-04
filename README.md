# ha-ecohome

This is a Home Assistant integration for the [New Energy
Eco-Home](https://ehome.ne01.com/) heat pump API, which is used (among others)
by Batavia Heat heat pumps in the Netherlands.

## Installation

You can install this by adding a custom integration repository to Home
Assistant, or by searching for Eco-Home in the HACS. Alternatively, you can copy
the `custom_components/ecohome` directory into your `config/custom_components`
directory inside Home Assistant.

Then, you can add the integration inside Home Assistant (search for Eco-Home).
This requires your username and password. If you have only one device, it is
immediately added; if you have multiple you can select which ones to add.
Devices shared with you cannot be added yet, but this is probably an easy fix.

## Development

### Releases

- Update version number in `pyproject.toml` and
  `custom_components/ecohome/manifest.json`. I try to keep the version
  number in sync with the Python `ecohome` library if possible.
- Run `uv sync`, commit and push all changes
- Create a tag and github release: `gh release create v0.1.2 --title "v0.1.2" --generate-notes`
- The new version should be indexed by HACS automatically.
