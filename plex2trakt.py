#!/usr/bin/python

from urlparse import urlparse
from plexapi.server import PlexServer
import json
import time
from trakt import Trakt
import logging
import yaml
import sys

log_format = '%(asctime)s\t%(levelname)s\t%(module)s\t%(message)s'
logging.basicConfig(format=log_format)
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

with open('config.yml', 'r') as f:
    config = yaml.load(f)

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
    #while time.time() - polling_start < polling_expire:
    while not p.has_expired():
        # parse=False in order to retrieve status code and suppress log.WARNING
        token_response = Trakt['oauth/device'].token(code_response['device_code'], parse=False)
        if token_response.status_code == 200:
            p.stop()
            print 'token_response', token_response
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
    print 'Manually add trakt access_token %(access_token)s to your config.yml' % token_response.json()
    raw_input("Press Enter to continue...")

trakt_username = config['trakt']['username']
plex = PlexServer(config['plex']['baseurl'], config['plex']['token'])
for search in config['search']:
    trakt_list_name = search['trakt_list_name']
    plex_library = plex.library.section(search['source_library'])
    log.info('%s: Gathering items from Plex.' % trakt_list_name)
    #if plex_library.type == 'movie':
    if plex_library.type in ('movie', 'shows'):
        if plex_library.type == 'movie':
            trakt_list_type = 'movies'
        elif plex_library.type == 'show':
            trakt_list_type = 'shows'
        trakt_items = {trakt_list_type: []}
        for item in plex_library.search(**search['filters']):
            guid = urlparse(item.guid)
            log.debug('Adding: %s.' % item.title)
            # Looking for imdb, tmdb, or tvdb
            id_type = guid.scheme.split('.')[-1]
            if id_type in ('imdb', 'themoviedb', 'tvdb'):
                trakt_items[trakt_list_type].append({'ids': {id_type: guid.netloc}})
            else:
                log.warning("Unknown agent for %s. Skipping." % item.title)
    if trakt_list_name not in [lst.name for lst in Trakt['users/*/lists'].get(trakt_username)]:
        log.info('%s: Creating list.' % trakt_list_name)
        Trakt['users/*/lists'].create(trakt_username, trakt_list_name)

    log.info('%s: Adding items to list.' % trakt_list_name)
    Trakt['users/*/lists/*'].add(trakt_username, trakt_list_name, trakt_items)
    log.info('%s: List complete.' % trakt_list_name)

