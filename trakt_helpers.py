from trakt import Trakt

import json
import os
import six
import copy
import ruamel.yaml

import logging
log = logging.getLogger(__name__)

def authenticate(authorization=None):

    if authorization['access_token']:
        # Test authorization
        with Trakt.configuration.oauth.from_response(authorization, refresh=True):
            if Trakt['users/settings']:
                # Successful authorization
                return authorization

    print('Navigate to: %s' % Trakt['oauth'].authorize_url('urn:ietf:wg:oauth:2.0:oob'))

    code = six.moves.input('Authorization code: ')
    if not code:
        exit(1)

    authorization = Trakt['oauth'].token(code, 'urn:ietf:wg:oauth:2.0:oob')
    if not authorization:
        exit(1)

    log.debug('Authorization: {}'.format(authorization))
    return authorization

def save_authorization(config_file, authorization):
    ruamel.yaml.YAML().allow_duplicate_keys = True
    from ruamel.yaml.util import load_yaml_guess_indent
    config, ind, bsi = load_yaml_guess_indent(open(config_file))
    config['trakt']['authorization']['access_token'] = authorization['access_token']
    config['trakt']['authorization']['token_type'] = authorization['token_type']
    config['trakt']['authorization']['expires_in'] = authorization['expires_in']
    config['trakt']['authorization']['refresh_token'] = authorization['refresh_token']
    config['trakt']['authorization']['scope'] = authorization['scope']
    config['trakt']['authorization']['created_at'] = authorization['created_at']
    log.info('Saving authorization information to {}'.format(config_file))
    ruamel.yaml.round_trip_dump(
        config,
        open(config_file, 'w'),
        indent=ind,
        block_seq_indent=bsi
    )