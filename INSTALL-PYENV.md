# Automated Pyenv Installation Guide for Armbian

This guide provides steps for automatically installing `pyenv` on Armbian using a shell script, along with necessary system dependencies.

## Prerequisites

Armbian is based on Debian/Ubuntu, so we use `apt-get` for package management.

## Installation Steps

### 1. Install System Dependencies

Before using `pyenv` to compile different Python versions, you must install required system libraries.

Open a terminal and run the following commands:

```bash
sudo apt-get update
sudo apt-get install -y build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev make openssl
```



### 2. Run the Automated Pyenv Installer
The pyenv-installer project provides a convenient shell script that automates the cloning of the pyenv repository and sets up the initial directory structure.
Execute the following command in your terminal:

```bash
curl https://pyenv.run | bash
```
