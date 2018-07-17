#!/usr/bin/env python
# -*- coding: utf-8 -*-

from urlparse import urlparse
from plexapi.server import PlexServer
import json
import time
from trakt import Trakt
import logging
import ruamel.yaml
import sys

config_file = 'config.yml'
from ruamel.yaml.util import load_yaml_guess_indent
config, ind, bsi = load_yaml_guess_indent(open(config_file))

log_format = '%(asctime)s - %(levelname)-8s - %(module)-16s - %(message)s'
logging.basicConfig(format=log_format)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG if config['debug'] else logging.INFO)

Trakt.configuration.defaults.client(
    id = config['trakt']['client_id'],
    secret = config['trakt']['client_secret']
)
Trakt.configuration.defaults.http(
    retry = True
)

if config['trakt']['access_token']:
    Trakt.configuration.defaults.oauth.from_response(config['trakt'])
else:
    code_response = Trakt['oauth/device'].code()
    print "Go to %(verification_url)s and enter user code: %(user_code)s" % code_response

    polling_start = time.time()
    polling_interval = code_response['interval']
    polling_expire = code_response['expires_in']
    p = Trakt['oauth/device'].poll(parse=False, **code_response)
    p.start()

    # There's probably a better way to implement polling.
    while not p.has_expired():
        # parse=False in order to retrieve status code and suppress log.WARNING
        token_response = Trakt['oauth/device'].token(code_response['device_code'], parse=False)
        if token_response.status_code == 200:
            p.stop()
            break
        elif token_response.status_code == 400:
            log.debug('Waiting on authorization.')
        elif token_response.status_code == 404:
            log.error('Invalid code entered. Aborting.')
            sys.exit()
        elif token_response.status_code == 409:
            log.error('Code already used. Aborting.')
            sys.exit()
        elif token_response.status_code == 410:
            log.error('Token expired. Aborting.')
            sys.exit()
        elif token_response.status_code == 418:
            log.error('Access was denied. Aborting.')
            sys.exit()
        elif token_response.status_code == 419:
            log.debug('Polling too quickly.')
            sys.exit()
        time.sleep(code_response['interval'])
    if p.has_expired():
        log.error('Token expired. Aborting.')
        sys.exit()
    Trakt.configuration.defaults.oauth.from_response(token_response.json())
    log.info('Updating %s with OAuth access token.' % config_file)
    config['trakt']['access_token'] = token_response.json()['access_token']
    ruamel.yaml.round_trip_dump(config,
                                open(config_file, 'w'), 
                                indent=ind,
                                block_seq_indent=bsi)
    raw_input("Press Enter to continue...")

trakt_username = config['trakt']['username']
plex = PlexServer(config['plex']['baseurl'], config['plex']['token'])
for search in config['search']:
    trakt_list_name = search['trakt_list_name']
    plex_library = plex.library.section(search['source_library'])
    log.info('%s: Gathering items from Plex.' % trakt_list_name)
    if plex_library.type in ('movie', 'shows'):
        if plex_library.type == 'movie':
            trakt_list_type = 'movies'
        elif plex_library.type == 'show':
            trakt_list_type = 'shows'
        trakt_items = {trakt_list_type: []}
        for item in plex_library.search(**search['filters']):
            guid = urlparse(item.guid)
            log.debug('Adding: %s' % item.title)
            # Looking for imdb, tmdb, or tvdb
            id_type = guid.scheme.split('.')[-1]
            if id_type in ('imdb', 'themoviedb', 'tvdb'):
                trakt_items[trakt_list_type].append({'ids': {id_type: guid.netloc}})
            else:
                log.warning("Unknown agent for %s. Skipping." % item.title)

    # Create list if it doesn't exist
    if trakt_list_name not in [lst.name for lst in Trakt['users/*/lists'].get(trakt_username)]:
        log.info('%s: Creating list.' % trakt_list_name)
        Trakt['users/*/lists'].create(trakt_username, trakt_list_name)

    # Get list slug to allow future API calls
    for lst in Trakt['users/*/lists'].get(trakt_username):
        if lst.name == trakt_list_name:
            for ids in lst.keys:
                if ids[0] == 'slug':
                    trakt_list_slug = ids[1]
                    log.debug('List slug: %s' % trakt_list_slug)
                    break
            break

    if search['trakt_list_privacy'] in ('friends', 'public'):
        # Public required if using Python-PlexLibrary
        log.info('%s: Updating privacy mode.' % search['trakt_list_name'])
        Trakt['users/*/lists/*'].update(trakt_username,
                                        trakt_list_slug,
                                        privacy=search['trakt_list_privacy']) 
    else:
        # Defaults to private
        pass
    
    log.info('%s: Adding items to list.' % trakt_list_name)
    Trakt['users/*/lists/*'].add(trakt_username, trakt_list_slug, trakt_items)
    log.info('%s: List creation complete.' % trakt_list_name)
