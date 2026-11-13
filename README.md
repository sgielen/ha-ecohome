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

After this, you can search for Eco-Home, and download and install
from there.

If you need to add this repository as a custom repository for whichever reason,
you can do so with the following settings:

- Repository: https://github.com/sgielen/ha-ecohome
- Type: Integration

### Installing yourself

Alternatively, you can copy the `custom_components/ecohome` directory from this
repository directly into your `config/custom_components` directory inside Home
Assistant.

### Configuration

After installation, you can add the integration inside Home Assistant settings
-> Devices and Services, search for Eco-Home.  This requires your username and
password. All devices in your account are added, including devices that other
users have shared with you.

If you don't want a device in Home Assistant, open its device page and choose
"Disable" from the ⋮ menu. The integration then stops fetching data for it.
To enable it again, find it under Settings -> Devices and Services -> Devices
(it may be hidden by the filter for disabled devices); Home Assistant reloads
the integration automatically after about 30 seconds.

### Language

The names of the sensors and settings come from Eco-Home itself, in the language
of Home Assistant. Eco-Home supports Chinese, Dutch, English, French, German,
Italian, Polish, Portuguese, Russian and Spanish. If the language is unsupported
by the Eco-Home API, the fallback language is Dutch. When you change the language
of Home Assistant, the integration reloads to pick up the new names.

To use a different language than Home Assistant, open the integration's options
(Settings -> Devices and Services -> Eco-Home -> Configure) and enter a language
such as `en`, `nl` or `fr`. Leave the field empty to follow Home Assistant again.

Changing the language changes the names of the entities, but not their entity
IDs, so automations and dashboards keep working. Names you have given entities
yourself are kept as well. In some languages Eco-Home gives different sensors
the same name; in French, for example, both the room and the outdoor temperature
are called "Température ambiante". The integration then adds the sensor's
address to the name, such as "Température ambiante (1000)", so that you can
tell them apart.

Versions before 0.1.8 always showed Dutch names.

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
