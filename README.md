# ![main](calibre-plugin/images/plugin.svg) OverDrive Libby Plugin for calibre

OverDrive Libby is a plugin that allows you to directly import your Libby loans into [calibre](https://calibre-ebook.com/).

Requires calibre 6.

## Main Features

- Import the `.acsm` file for EPUB/PDF(DRM) book loans (see issue below)
- Import the `.epub` file for EPUB (open) book loans
- Import the `.epub` file for Magazines loans \[EXPERIMENTAL\]

This plugin also works with the [ACSM Input plugin](https://github.com/Leseratte10/acsm-calibre-plugin/) to convert `.acsm` files into `.epub`.

## Known Issues

- `.acsm` files imported into calibre results in epubs (via the [ACSM Input plugin](https://github.com/Leseratte10/acsm-calibre-plugin/issues/56)) that do not have calibre metadata [calibrebug#2025355](https://bugs.launchpad.net/calibre/+bug/2025355). A [simple workaround](https://github.com/ping/libby-calibre-plugin/issues/1) is available.

## Install

Open Preferences > Plugins > Get new plugins, and install the "OverDrive Libby" User interface action plugin.

You may also download the latest plugin zip file from Releases and install the plugin manually, then restart calibre as described in the [Introduction to Plugins](https://www.mobileread.com/forums/showthread.php?t=118680) thread. 

## Setup

Open the plugin customisation settings (from calibre Preferences > Advanced: Plugins > Search for "overdrive libby" and then click on the "Customize plugin" button).

To configure this plugin, you must already be using Libby on a [compatible](https://help.libbyapp.com/en-us/6105.htm) device.

![settings](images/settings.png)

You will need to get a Libby setup code by following the instructions [here](https://help.libbyapp.com/en-us/6070.htm). Enter the code into the plugin settings and click "OK". If you encounter an error, the code may have expired. Get a new one and try again.

You should only need to do this setup once. Then add the plugin to the toolbar/menubar as you wish.

### Help

- Hide Magazines: Don't list magazine loans
- Hide Ebooks: Don't list ebook loans
- Prefer Open Formats: Choose DRM-free formats if available
- Hide books already in library: Hide loans that are already in your library

## Usage

![main](images/main.png)

Launch the OverDrive Libby plugin UI and select the loans you wish to download. Then click on the Download button.

Each selected loan will then be downloaded in its own calibre job. When the job completes, the loan book file should be in your library.

Only downloadable loans will be listed. If the loan does not have a downloadable format, or has previously been sent to your Kindle, it will not be displayed.

## Disclaimer

This is not affliated, endorsed or certified by OverDrive. To use this plugin, you must already have access to OverDrive services via a valid library account. Use at your own risk.
