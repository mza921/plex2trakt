#!/usr/bin/env python
# -*- coding: utf-8 -*-

from urlparse import urlparse
from plexapi.server import PlexServer
import json
import os
import time
import trakt
import logging
import ruamel.yaml
import sys

config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yml')
from ruamel.yaml.util import load_yaml_guess_indent
config, ind, bsi = load_yaml_guess_indent(open(config_file))

log_format = '%(asctime)s - %(levelname)-8s - %(module)-16s - %(message)s'
logging.basicConfig(format=log_format)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG if config['debug'] else logging.INFO)

t = trakt.Trakt(config)
trakt_username = config['trakt']['username']
plex = PlexServer(config['plex']['baseurl'], config['plex']['token'])
for search in config['search']:
    trakt_list_name = search['trakt_list_name']
    plex_library = plex.library.section(search['source_library'])
    log.info('%s: Gathering items from Plex.' % trakt_list_name)
    if plex_library.type in ('movie', 'show'):
        if plex_library.type == 'movie':
            trakt_list_type = 'movies'
        elif plex_library.type == 'show':
            trakt_list_type = 'shows'
        trakt_items = {trakt_list_type: []}
        for item in plex_library.search(**search['filters']):
            guid = urlparse(item.guid)
            log.debug('Adding: %s' % item.title)
            # Looking for imdb, tmdb, or thetvdb
            id_type = guid.scheme.split('.')[-1]
            if id_type in ('imdb', 'themoviedb'):
                trakt_items[trakt_list_type].append({'ids': {id_type: guid.netloc}})
            elif id_type in ('thetvdb'):
                trakt_items[trakt_list_type].append({'ids': {'tvdb': guid.netloc}})
            else:
                log.warning("Unknown agent for %s. Skipping." % item.title)

    # Create list if it doesn't exist
    if trakt_list_name not in [trakt_list['name'] for trakt_list in t.get_lists()]:
        log.info('%s: Creating list.' % trakt_list_name)
        t.create_list(trakt_list_name)

    # Get list slug to allow future API calls
    for trakt_list in t.get_lists():
        if trakt_list['name'] == trakt_list_name:
            trakt_list_slug = trakt_list['ids']['slug']
            break

    if search['trakt_list_privacy'] in ('friends', 'public'):
        # Public required if using Python-PlexLibrary
        log.info('%s: Updating privacy mode.' % search['trakt_list_name'])
        t.update_list_privacy(trakt_list_slug, privacy=search['trakt_list_privacy']) 
    else:
        # Defaults to private
        pass
    
    log.info('%s: Adding items to list.' % trakt_list_name)
    t.add_list_items(trakt_list_slug, trakt_items)
    log.info('%s: List creation complete.' % trakt_list_name)
