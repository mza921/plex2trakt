import backoff
import json
import os
import requests
import ruamel.yaml
import yaml
from pprint import pprint


class Trakt:

    def __init__(self, config):
        self.username = config['trakt']['username']
        self.client_id = config['trakt']['client_id']
        self.client_secret = config['trakt']['client_secret']
        self.access_token = config['trakt']['access_token']
        if not self.access_token:
            g = self.generate_device_code().json()
            self.device_code = g['device_code']
            self.polling_interval = g['interval']
            self.polling_expiration = g['expires_in']
            self.access_token = self.poll_for_access_token().json()['access_token']
            self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yml')
            self.save_access_token(self.config_file)

    def headers(self):
        return {
            'Content-type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': self.client_id,
            'Authorization': 'Bearer %s' % self.access_token
        }

    def generate_device_code(self):
        url = 'https://api.trakt.tv/oauth/device/code'
        payload = {'client_id': self.client_id}
        r = requests.post(url, json=payload, headers=self.headers())
        print 'Go to %(verification_url)s and enter %(user_code)s' % r.json()
        return r

    @backoff.on_predicate(backoff.constant, lambda x: x.status_code == 400, interval=5)
    def poll_for_access_token(self):
        url = 'https://api.trakt.tv/oauth/device/token'
        payload = {
            'code': self.device_code,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        r = requests.post(url, json=payload, headers=self.headers())
        return r

    def save_access_token(self, config_file):
        from ruamel.yaml.util import load_yaml_guess_indent
        config, ind, bsi = load_yaml_guess_indent(open(config_file))
        config['trakt']['access_token'] = self.access_token
        ruamel.yaml.round_trip_dump(
            config,
            open(config_file, 'w'),
            indent=ind,
            block_seq_indent=bsi
        )

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=5)
    def get_lists(self):
        url = 'https://api.trakt.tv/users/%s/lists' % self.username
        params = {'id': self.username}
        r = requests.get(url, params=params, headers=self.headers())
        return r.json()

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=5)
    def create_list(self, list_name, privacy='private'):
        url = 'https://api.trakt.tv/users/%s/lists' % self.username
        params = {'id': self.username}
        payload = {
            'name': list_name,
            'privacy': privacy
        }
        r = requests.post(url, params=params, json=payload, headers=self.headers())
        return r.json()

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=5)
    def update_list_privacy(self, list_id, privacy):
        url = 'https://api.trakt.tv/users/%s/lists/%s' % (self.username, list_id)
        params = {'id': self.username}
        payload = {
            'privacy': privacy
        }
        r = requests.put(url, params=params, json=payload, headers=self.headers())
        return r.json()

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=5)
    def get_list_items(self, list_id, list_type):
        url = 'https://api.trakt.tv/users/%s/lists/%s/items/%s' % (self.username, list_id, list_type)
        params = {'id': self.username, 'list_id': list_id, 'type': list_type, 'extended': 'full'}
        r = requests.get(url, params=params, headers=self.headers())
        return r.json()

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=5)
    def add_list_items(self, list_id, items):
        url = 'https://api.trakt.tv/users/%s/lists/%s/items' % (self.username, list_id)
        params = {'id': self.username, 'list_id': list_id}
        r = requests.post(url, json=items, params=params, headers=self.headers())
        return r.json()
