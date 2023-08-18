HLS-data-project
==============================

A short description of the project.

--------

## Setup

### The environment

To run the notebooks you need to create an environment with the dependencies. There are two options:

#### Docker

If you have [docker](https://docs.docker.com/engine/install/) in your system,
you run a jupyter lab server with:

``` bash
docker compose up --build
```

And if you want to get into the container, use a terminal in jupyter lab,
vscode remote development or run this command:

```shell
docker exec -it hls_data_project_notebooks /bin/bash
```

#### Conda environment

Create the environment with:

``` bash
mamba env create -n hls_data_project -f environment.yml
```

This will create an environment called HLS-data-project with a common set of dependencies.

### `git` (if needed) and pre-commit hooks

If this project is a new and standalone (not a module in a bigger project), you need to initialize git:

``` bash
git init
```

If the project is already in a git repository, you can skip this step.

To install the **pre-commit hooks**, with the environment activated and in the project root directory, run:

``` bash
pre-commit install
```

### Setting up a netrc File
You will need a netrc file containing your NASA Earthdata Login credentials in order to execute this tutorial. If you want to manually create your own netrc file, download the [.netrc file template](https://git.earthdata.nasa.gov/projects/LPDUR/repos/daac_data_download_python/browse/.netrc), add your credentials, and save to your home directory. If you want to use the python script to set up a netrc file but do not need to download any files, copy/clone/download the [EarthdataLoginSetup.py](https://git.earthdata.nasa.gov/projects/LPDUR/repos/daac_data_download_python/browse/EarthdataLoginSetup.py) script and execute it: `python EarthdataLoginSetup.py`. You will be prompted for your NASA Earthdata Login Username and Password, hit enter once you have submitted your credentials.

## Update the environment

If you need to update the environment installing a new package, you simply do it with:

``` bash
mamba install [package]  # or `pip install [package]` if you want to install it via pip
```

then update the environment.yml file so others can clone your environment with:

``` bash
mamba env export --no-builds -f environment.yml
```