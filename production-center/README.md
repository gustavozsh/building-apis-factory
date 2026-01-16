<!-- omit from toc -->
# cadastra_core
Proprietary Cadastra library for all things data: integration, security, quality and much more!

<!-- omit from toc -->
## Table of contents
- [Changelog](#changelog)
- [Available modules](#available-modules)
- [Configuring Artifact Registry](#configuring-artifact-registry)
  - [How keyring works](#how-keyring-works)
  - [Setting up keyring](#setting-up-keyring)
- [Installing the package](#installing-the-package)
- [Requiring the package in your project](#requiring-the-package-in-your-project)

## Changelog
The changelog is available [HERE IN THIS FILE.](./CHANGELOG.md)
## Available modules
These are the currently available modules. To learn how to use them, refer to the respective README file by clicking the links.
- [Amazon Ads](./cadastra_core/AmazonAds/)
- [BigQuery](./cadastra_core/BigQuery/)
- [Bing Ads](./cadastra_core/Bing/)
- [Criteo](./cadastra_core/Criteo/)
- [DV360](./cadastra_core/DV360/)
- [Google Ads](./cadastra_core/GoogleAds/)
- [Google Analytics 4](./cadastra_core/GoogleAnalytics4/)
- [Meta](./cadastra_core/Meta/)
- [Mercado Livre](./cadastra_core/MercadoLivre/)
- [RTB House](./cadastra_core/Rtbhouse/)
- [Search Ads 360](./cadastra_core/SearchAds360/)
- [Secret Manager](./cadastra_core/SecretManager/)
- [TikTok](./cadastra_core/TikTok/)
- [Utilities](./cadastra_core/Utils/)

## Configuring Artifact Registry

We are using Google Cloud Artifact Registry to host our private repo. Because of this, you'll need to setup authentication to access the Artifact Registry repository in your machine.

First of all, configure the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install#windows).

After you've installed and logged in on the Google Cloud CLI, you'll then proceed with the following steps to install the **keyring** python library and configure pip to look for your private repo index.

### How keyring works
*The following steps are based off [this Google documentation](https://cloud.google.com/artifact-registry/docs/python/authentication?hl=pt-br#keyring).*

The Python keyring library provides applications with a way to access keyring backends, meaning operating system and third-party credential stores.

Artifact Registry provides the keyrings.google-artifactregistry-auth keyring backend to handle authentication with Artifact Registry repositories.

#### Credential search order
When you use the Artifact Registry keyring backend, your credentials are not stored in your Python project. Instead, Artifact Registry searches for credentials in the following order:

1. Credentials defined in the GOOGLE_APPLICATION_CREDENTIALS environment variable.
2. Credentials that the default service account for Compute Engine, Google Kubernetes Engine, Cloud Run, App Engine, or Cloud Run functions provides.
3. Credentials provided by the Google Cloud CLI, including user credentials from the command `gcloud auth application-default login`.

### Setting up keyring
To set up authentication with the Artifact Registry keyring backend:

1. Install the keyring library.
```
pip install keyring
```

2. Install the Artifact Registry backend.
```
pip install keyrings.google-artifactregistry-auth
```
3. List backends to confirm the installation.
```
keyring --list-backends
```
The list should include
```
ChainerBackend(priority:10)
GooglePythonAuth(priority: 9)
```
4. Add the following settings to the **.pypirc** file. The default location is:

- **Linux and macOS:** $HOME/.pypirc
- **Windows:** %USERPROFILE%/.pypirc
```
[distutils]
index-servers =
    cadastra

[cadastra]
repository: https://us-python.pkg.dev/cadastra-prd/cadastra/
```
5. Finally, let's change the **pip configuration file**. 
Add the following contents to your file:
```
[global]
extra-index-url = https://us-python.pkg.dev/cadastra-prd/cadastra/simple/
```
The file location will depend whether you want to configure system-wide or inside virtual environments.

_**System-wide pip config file (does not apply to virtual environments):**_

- **Unix:** $HOME/.config/pip/pip.conf or $HOME/.pip/pip.conf
- **macOS:** /Library/Application Support/pip/pip.conf or $HOME/.config/pip/pip.conf
- **Windows:** %USERPROFILE%\pip\pip.ini

_**Virtual environment pip config file**_

- **Unix and macOS:** *path_to_your_virtual_env*/pip.conf
- **Windows:** *path_to_your_virtual_env*\pip.ini

Your "pip" executable won't be at the same location as its config file. If you can't find these files or folders in your system, you can create them manually making sure to match the paths stated above.

***You're done!***

## Installing the package
Now that you have configured the Google Cloud CLI to handle authentication and pip to look at our private repository, you can now simply install the package by issuing the command:

```
python -m pip install cadastra_core
```

## Requiring the package in your project
If you are using our package in your project, you'll need to reference it in your **requirements.txt** file.

To do so, paste the following into the very first line of your **requirements.txt** file:

`--extra-index-url https://us-python.pkg.dev/cadastra-prd/cadastra/simple`

For example, when deploying to Google Cloud Run Functions, your requirements.txt file should look something like this:
```
--extra-index-url https://us-python.pkg.dev/cadastra-prd/cadastra/simple
cadastra_core
functions-framework==3.*
```

**This package won't work if used outside our Google Cloud projects or in a machine with a user that's not allowed to access our private repo.**