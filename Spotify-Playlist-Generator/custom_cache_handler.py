from spotipy import CacheHandler
import json
import os
import logging


class CustomCacheFileHandler(CacheHandler):
    """
    Handles reading and writing cached Spotify authorization tokens
    as json files on disk. The cache file name is dynamically determined
    based on the credentials index provided.
    """

    def __init__(self,
                 credentials_index,
                 cache_dir='cache',
                 encoder_cls=None):
        """
        Parameters:
             * credentials_index: The index of the credentials in the
                                  `credentials_dicts` list.
             * cache_dir: The directory where cache files are stored.
                          Defaults to '.cache'.
             * encoder_cls: May be supplied as a means of overwriting the
                            default serializer used for writing tokens to disk.
        """
        self.credentials_index = credentials_index
        self.encoder_cls = encoder_cls
        cache_filename = f'.cache{credentials_index}'
        self.cache_path = os.path.join(cache_dir, cache_filename)

    def get_cached_token(self):
        token_info = None

        try:
            with open(self.cache_path, 'r') as f:
                token_info_string = f.read()
                token_info = json.loads(token_info_string)

        except FileNotFoundError:
            logging.debug("Cache does not exist at: %s", self.cache_path)
        except IOError:
            logging.warning("Couldn't read cache at: %s", self.cache_path)

        return token_info

    def save_token_to_cache(self, token_info):
        try:
            with open(self.cache_path, 'w') as f:
                f.write(json.dumps(token_info, cls=self.encoder_cls))
        except IOError as e:
            logging.warning(f'Couldn\'t write token to cache at: %s: {e}', self.cache_path)
