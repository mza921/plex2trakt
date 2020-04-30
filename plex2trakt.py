#!/usr/bin/env python
# -*- coding: utf-8 -*-

from urllib.parse import urlparse
from plexapi.server import PlexServer
import json
import os
import time
from trakt import Trakt
import logging
import ruamel.yaml
import sys
import config_tools

config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yml')
from ruamel.yaml.util import load_yaml_guess_indent
config, ind, bsi = load_yaml_guess_indent(open(config_file))

recipe_file = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'recipes',
    sys.argv[1] + '.yml')
with open(recipe_file) as r:
    recipe = ruamel.yaml.safe_load(r)

log_format = '%(asctime)s - %(levelname)-8s - %(module)-16s - %(message)s'
logging.basicConfig(format=log_format)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG if config['debug'] else logging.INFO)

config_tools.TraktClient(config_file)
plex = PlexServer(config['plex']['baseurl'], config['plex']['token'], timeout=60)

list_name = recipe['name']
plex_library = plex.library.section(recipe['source_library'])
log.info('%s: Gathering items from Plex.' % list_name)
if plex_library.type in ('movie', 'show'):
    if plex_library.type == 'movie':
        list_type = 'movies'
        item_type = 'movie'
    elif plex_library.type == 'show':
        list_type = 'shows'
        item_type = 'show'
    trakt_items = {list_type: []}
    whitelist_plex_items = []
    blacklist_plex_items = []
    if recipe['filter_source'] == 'plex':
        if 'whitelist' in recipe:
            whitelist_plex_items = plex_library.search(**recipe['whitelist'])
        else:
            whitelist_plex_items = plex_library.all()
        if 'blacklist' in recipe:
            blacklist_plex_items = plex_library.search(**recipe['blacklist'])
        plex_items = [i for i in whitelist_plex_items if i not in blacklist_plex_items]
    else:
        # Include all items for filtering later
        plex_items = plex_library.all()
    for item in plex_items:
        guid = urlparse(item.guid)
        log.debug('Queuing: %s' % item.title)
        # Looking for imdb, tmdb, or thetvdb
        id_type = guid.scheme.split('.')[-1]
        if plex_library.type == 'movie':
            if id_type == 'imdb':
                trakt_items[list_type].append({'ids': {id_type: guid.netloc}})
            elif id_type == 'themoviedb':
                trakt_items[list_type].append({'ids': {'tmdb': guid.netloc}})
            else:
                log.warning("Unknown agent for %s. Skipping." % item.title)
        elif plex_library.type == 'show':
            if id_type in ('themoviedb'):
                trakt_items[list_type].append({'ids': {'tmdb': guid.netloc}})
            elif id_type in ('thetvdb'):
                trakt_items[list_type].append({'ids': {'tvdb': guid.netloc}})
            else:
                log.warning("Unknown agent for %s. Skipping." % item.title)
        else:
            log.warning("Unsupported library type for %s. Skipping." % item.title)
    log.info('Plex items found: %d' % len(plex_items))
    log.info('Trakt items to add: %d' % len(trakt_items[list_type]))

# Create list if it doesn't exist
if list_name not in [trakt_list.name for trakt_list in Trakt['users/me/lists'].get()]:
    log.info('%s: Creating list.' % list_name)
    t = Trakt['users/me/lists'].create(list_name)
else:
    # Get list slug to allow future API calls
    for trakt_list in Trakt['users/me/lists'].get():
        if trakt_list.name == list_name:
            t = Trakt['users/me/lists/*'].get(trakt_list.id)
            break

if recipe['filter_source'] == 'plex':
    log.info('%s: Adding items to list.' % list_name)
else:
    log.debug('%s: Temporarily adding items to list.' % list_name)
t.add(trakt_items)

# Trakt filters
if recipe['filter_source'] == 'trakt':
    whitelist_post = {list_type: []}
    blacklist_post = {list_type: []}
    #all_trakt_items = t.get_list_items(trakt_list_slug, list_type)
    all_trakt_items = t.items(extended='full')
    for trakt_item in all_trakt_items:
        for filter_type in ('whitelist', 'blacklist'):
            if filter_type in recipe:
                for filter_name in recipe[filter_type]:
                    for filter_value in recipe[filter_type][filter_name]:
                        # Needed in case the value is empty
                        # if trakt_item.to_dict()[filter_name]:
                        if filter_name in trakt_item.to_dict():
                            if filter_value in trakt_item.to_dict()[filter_name]:
                                if filter_type == 'whitelist':
                                    # whitelist_post[list_type].append({'ids': trakt_item[item_type]['ids']})
                                    whitelist_post[list_type].append({'ids': trakt_item.to_dict()['ids']})
                                    # whitelist_post[list_type].append({'ids': trakt_item.pk})
                                elif filter_type == 'blacklist':
                                    # blacklist_post[list_type].append({'ids': trakt_item[item_type]['ids']})
                                    blacklist_post[list_type].append({'ids': trakt_item.to_dict()['ids']})
                                    # blacklist_post[list_type].append({'ids': trakt_item.pk})
                                break
            else:
                # Include everything
                if filter_type == 'whitelist':
                    # whitelist_post[list_type].append({'ids': trakt_item[item_type]['ids']})
                    whitelist_post[list_type].append({'ids': trakt_item.to_dict()['ids']})
                    # whitelist_post[list_type].append({'ids': trakt_item.pk})

    final_post = {}
    final_post[list_type] = [i for i in whitelist_post[list_type] if i not in blacklist_post[list_type]]
    log.debug('%s: Deleting list.' % list_name)
    t.delete()
    log.debug('%s: Recreating list.' % list_name)
    t = Trakt['users/me/lists'].create(list_name)
    log.info('%s: Adding filtered items to list.' % list_name)
    t.add(final_post)

# if recipe['privacy'] in ('friends', 'public'):
#     # Public required if using Python-PlexLibrary
#     log.info('%s: Updating privacy mode.' % list_name)
#     t.update_list_privacy(trakt_list_slug, privacy=recipe['privacy'])
# else:
#     # Defaults to private
#     pass

list_size = len(t.items())
log.info('%s: List creation complete (%d %s items).' % (list_name, list_size, item_type))