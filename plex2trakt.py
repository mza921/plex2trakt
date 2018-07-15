#!/usr/bin/python

from urlparse import urlparse
from plexapi.server import PlexServer
import os
import json
import time
from trakt import Trakt
import logging
import yaml
from pprint import pprint

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

with open('config.yml', 'r') as f:
    config = yaml.load(f)

Trakt.configuration.defaults.client(
    id = config['trakt']['client_id'],
    secret = config['trakt']['client_secret']
)

if config['trakt']['access_token']:
    Trakt.configuration.defaults.oauth.from_response(config['trakt'])
else:
    code_response = Trakt['oauth/device'].code()
    print "Go to %(verification_url)s and enter user code: %(user_code)s" % code_response
    polling_start = time.time()
    polling_interval = code_response['interval']
    polling_expire = code_response['expires_in']
    p = Trakt['oauth/device'].poll(**code_response)
    while time.time() - polling_start < polling_expire:
        #try token
        token_response = Trakt['oauth/device'].token(code_response['device_code'])
        if token_response:
            p.stop()
            break
        time.sleep(code_response['interval'])
    Trakt.configuration.defaults.oauth.from_response(token_response)

trakt_username = config['trakt']['username']
plex = PlexServer(config['plex']['baseurl'], config['plex']['token'])
for search in config['search']:
    trakt_list_name = search['trakt_list_name']
    plex_library = plex.library.section(search['source_library'])
    if plex_library.type == 'movie':
        imdb_ids = []
        tmdb_ids = []
        trakt_items = {'movies': []}
        for item in plex_library.search(**search['filters']):
            guid = urlparse(item.guid)
            if 'imdb' in guid.scheme:
                trakt_items['movies'].append({'ids': {'imdb': guid.netloc}})
            elif 'themoviedb' in guid.scheme:
                trakt_items['movies'].append({'ids': {'tmdb': guid.netloc}})
            #else:
                #log.warning("Unknown agent for %s. Skipping.") % item.title
    elif plex_library.type == 'show':
        tvdb_ids = []
        trakt_items = {'shows': []}
        for item in plex_library.search(**search['filters']):
            guid = urlparse(item.guid)
            if 'tvdb' in guid.scheme:
                trakt_items['shows'].append({'ids': {'tvdb': guid.netloc}})
            elif 'themoviedb' in guid.scheme:
                trakt_items['shows'].append({'ids': {'tmdb': guid.netloc}})
            #else:
                #log.warning("Unknown agent for %s. Skipping.") % item.title
    if trakt_list_name not in [lst.name for lst in Trakt['users/*/lists'].get(trakt_username)]:
        Trakt['users/*/lists'].create(trakt_username, trakt_list_name)
    else:
        Trakt['users/*/lists/*'].add(trakt_username, trakt_list_name, trakt_items)
