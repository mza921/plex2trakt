# -*- coding: UTF-8 -*-
from trakt import Trakt
import trakt_helpers
import ruamel.yaml

class Config:
    def __init__(self, config_path):
        #self.config_path = os.path.join(os.getcwd(), 'config.yml')
        self.config_path = config_path
        with open(self.config_path, 'rt', encoding='utf-8') as yml:
            self.data = ruamel.yaml.safe_load(yml)
        self.trakt = self.data['trakt']


class TraktClient:
    def __init__(self, config_path):
        config = Config(config_path).trakt
        self.client_id = config['client_id']
        self.client_secret = config['client_secret']
        self.authorization = config['authorization']
        Trakt.configuration.defaults.client(self.client_id, self.client_secret)
        Trakt.configuration.defaults.http(retry=True, timeout=(6.05, 60))
        # Try the token from the config
        self.updated_authorization = trakt_helpers.authenticate(self.authorization)
        Trakt.configuration.defaults.oauth.from_response(self.updated_authorization)
        if self.updated_authorization != self.authorization:
            trakt_helpers.save_authorization(Config(config_path).config_path, self.updated_authorization)