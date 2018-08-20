# plex2trakt
Export filtered Plex libraries to Trakt lists. The Trakt lists can then be used with [Python-PlexLibrary](https://github.com/adamgot/python-plexlibrary) to create dynamic Plex libraries. Currently supports filtering based on either Plex or Trakt metadata.

## Requirements
1. Python 2.7
2. requirements.txt modules

## Installation  
#### 1. Base Install
1.  `git clone https://github.com/mza921/plex2trakt`
2. `cd plex2trakt`
3. `pip install -r requirements.txt`
#### 2. Create a Trakt application
1. [Create](https://trakt.tv/oauth/applications/new) a Trakt API application.
2. Enter a `Name` for the application.
3. Enter `urn:ietf:wg:oauth:2.0:oob` for `Redirect uri`.
4. Click the `SAVE APP` button.
5. Record the `Client ID` and `Client Secret`.  
## Configuration
1. `cp config.yml-template config.yml`
2. Fill in the following:

    *Under `trakt:`*  
    `username:`  
    `client_id:` (from above)  
    `client_secret:` (from above)
    
    *Under `plex:`*  
    `baseurl:`  
    `token:` (See [here](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/).)
3. Create desired recipes. See `recipes/examples` folder for ideas. Save in the `recipes` folder.
## Usage
From the plex2trakt directory,  
`plex2trakt <recipe_name>` (without .yml extension)  
  
On the initial run, follow the prompt to authorize the application.
## Examples
*Coming soon*
