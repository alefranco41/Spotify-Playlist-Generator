import pickle
from spotipy.oauth2 import SpotifyOAuth
import spotipy
from datetime import datetime
import math
import random
import os

def delete_cache():
    if os.path.exists('.cache'):
        os.remove('.cache')

def compute_recently_played_songs(spotify):
    #try to load the accumulated listening history (spotify API only allows to retrieve the last 50 songs of the listening history)
    try:
        with open("data/recently_played_songs.bin", "rb") as file:
            recently_played_songs = pickle.load(file)
    except FileNotFoundError:
        recently_played_songs = {'items': []}

    existing_song_keys = {(item['track']['id'], item['played_at']) for item in recently_played_songs['items']}

    #get the last 50 songs in the listening history and keep only the ones that have not been stored yet
    new_songs = [song for song in spotify.current_user_recently_played()['items'] if (song['track']['id'], song['played_at']) not in existing_song_keys]

    #add to the existing songs in the playlist the new ones
    recently_played_songs['items'].extend(new_songs)


    with open("data/recently_played_songs.bin", "wb") as file:
        pickle.dump(recently_played_songs, file)

    #order the listening history by decreasing playing timestamp
    recently_played_songs = sorted(recently_played_songs['items'], key=lambda x: x['played_at'], reverse=True)

    #remove consecutive duplicates and songs that have been played for too little time
    unique_songs = [recently_played_songs[0]] 
    for i in range(1, len(recently_played_songs)):
        current_song = recently_played_songs[i]
        previous_song = recently_played_songs[i - 1]

        #Compute the difference of the two timestamps
        current_time = datetime.fromisoformat(current_song['played_at'].rstrip('Z'))
        previous_time = datetime.fromisoformat(previous_song['played_at'].rstrip('Z'))

        time_difference = (previous_time - current_time).total_seconds()

        #We only keep different consecutive songs and songs that have been played for at least 30 seconds
        if current_song['track']['id'] != previous_song['track']['id'] and time_difference >= 30:
            unique_songs.append(current_song)

    recently_played_songs = unique_songs
    return recently_played_songs

#if the user provides a "StreamingHistory.json" file, then we use this function to filter the listening history.
#we order the listening history by decreasing playing timestamp
#we remove consecutive duplicates and songs that have been played for less than 50% of the its duration
def filter_listening_history_file(csv_data):
    valid_items = []
    for item in csv_data:
        try:
            item['endTime'] = datetime.strptime(item['endTime'], "%Y-%m-%d %H:%M")
            valid_items.append(item)
        except ValueError:
            csv_data.remove(item)
    
    recently_played_songs = sorted(valid_items, key=lambda x: x['endTime'], reverse=True)
    unique_songs = [recently_played_songs[0]]

    for i in range(1, len(recently_played_songs)):
        current_song = recently_played_songs[i]
        previous_song = recently_played_songs[i - 1]
        
        listen_percentage = math.floor(100 * (int(current_song['msPlayed']) / int(current_song['msDuration'])))
        if current_song['TrackID'] != previous_song['TrackID'] and listen_percentage >= 50:
            unique_songs.append(current_song)

    recently_played_songs = unique_songs
    return recently_played_songs

#Spotify application credentials
credentials_dicts = {
    'nignebotro@gufum.com': [
        {
            'client_id':'5d847817e3124f73915e4cb87add556f',
            'client_secret':'38db16b27bf24c82a30854c444afa305',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'29dc0e16554e46c5a3300033b3b41ba6',
            'client_secret':'0103646b260b4d8ea62d41dbe3a6893f',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'9ad3b2d2c4224269b45bed163a8d33c5',
            'client_secret':'e1d031337eb0428ca4d73e5648ecc883',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'9ade9099fe404413b8c55555c2e6dfe2',
            'client_secret':'b36dca72b4a84cf9b1fbec5d88980ffe',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'8f9d68c156854126bea2c193a509a6d1',
            'client_secret':'3d30eafe0d0c45d085c7cb62046e7742',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'minin11613@mnsaf.com': [
        {
            'client_id':'9d833544903241a89eb3dc527c04a65b',
            'client_secret':'1a9f316213684427903504abcb6f160d',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'876feec8313248339c441b74afc8881e',
            'client_secret':'c0b474dff1ad4be1a3b39d0b7aa52388',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'31a1733a1bf9470798d6dbfd0d8def4b',
            'client_secret':'3b36474f1742475d9e372144127a382e',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'23e49ac127204c91a1447551caa6aecc',
            'client_secret':'3ed7aa7843b44233bd000f0239278fcc',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'c899bbdb5b464e4ebafe64ee3cedb12c',
            'client_secret':'7dcf6f9de08f477bab7a851bb7ccb7d8',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'muydihispu@gufum.com': [
        {
            'client_id':'dab76c36dc3b4360aea8b0399c8b63ce',
            'client_secret':'f7b217c027a6484eb0ee4fd739f46db2',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'6f62643136294c08a9b2d39efdcfd3e4',
            'client_secret':'5212455fa41c43d4b46166ee2af46782',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'20b5136836584691ac30c16b726b7084',
            'client_secret':'47d0b1d1e1d142ec91c4abe9d5e62157',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'e503cd0074164a7896dab6102a3cd629',
            'client_secret':'506c9dafe0164dd69fd48337deea7cf4',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'23c8fac0463f4de7a0cc1e1e502674da',
            'client_secret':'0af031f96a314ec0bda57736d19c1c6e',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'alessandro.franceschini.2002@gmail.com': [
        {
            'client_id':'88af6dfe58a24ae5afd36cd35cff978c',
            'client_secret':'84202b1ec08442dea6899e16214d8242',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'69dddf2b92de442ab9af0b8910c36b01',
            'client_secret':'eb9d3663520446e99ca89ce0ca8da4ae',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'f95642ced4744ba89b32c0cb22629c0e',
            'client_secret':'0e1db2d43493486c97acb6ad07db3a36',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'149c7e56cf274adcaf2e57da5641f84c',
            'client_secret':'7ed5a6a8c6f449f099d3cc3cd62fba6c',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'b45b91203a334848ae2a6895e695fb56',
            'client_secret':'c53c8201ba8447f0b559e62ef142f310',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'difyekilmu@gufum.com': [
        {
            'client_id':'ea826b08362f43f791935bbc2894243e',
            'client_secret':'cce4a1c5e3c54e78ba11d4a314dd0d96',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'9a6e664c3a75401eb52df154f4fa00a6',
            'client_secret':'03b276b0b0144c39941aa886f42d7f4c',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'bb0f296a99d6424bbfe75e70fc3ddbbf',
            'client_secret':'b53c75a4c1ec4d0db17d511b481ab2e2',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'6bf7752c60494d51934e7e64f1cdb589',
            'client_secret':'fb542488f0ea4663ab381a18ef61f3ea',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'37f13d9a346b4acd9d2e0bd5b95f8db6',
            'client_secret':'0695d88adab142deb031de57c5c162a0',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'sugnehomle@gufum.com': [
        {
            'client_id':'5623265c5bd34ec4add7a937c4f5b170',
            'client_secret':'3ce4df2f77b14b6b901565f8c31db159',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'df46b0edd59b47b9b0fd93622f1f157b',
            'client_secret':'a3e3956789cc489a89a596edbe6d688e',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'dfba50cb07044a9880ed53c270cd2345',
            'client_secret':'9113f66783884e3cb83949a8f5d4fda5',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'e51360737d63433ebe0b2fb6b151a615',
            'client_secret':'21aba6385f46403282d516fcd2524974',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'6ade82872def40a5bc047abb641f2b9e',
            'client_secret':'2a7e2611f7114e2a9cc55bcd835395de',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'yukkulurke@gufum.com': [
        {
            'client_id':'ea2f060e1cb84b8a91b760900d26a017',
            'client_secret':'767dd245486f49949abff15b5931a537',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'93aa55435a2947358c57ad835ea9010d',
            'client_secret':'f416bf90eadc4939b750ebcb5ba731fe',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'cb35e8b288c34218bbb249241b212f31',
            'client_secret':'18cc00ae3dcd4b9fa20544a982ef3e02',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'6327b74bd21a4d9585d9261858d66fc5',
            'client_secret':'b6666439dd0440c3ace6fd42ac75fc4f',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'08849ea240ad4985a467f1533e5c78eb',
            'client_secret':'8e1c5eb683664828943bee92218d5786',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'cilmaharze@gufum.com': [
        {
            'client_id':'a861714994da45dd8570f3e0dd467147',
            'client_secret':'b5e3129d10a943dd8b3db61ab48a91a5',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'89b4a4ad3f9042789551632fa9cb1615',
            'client_secret':'2169360b4f4f4c20923296d6ef46f7fa',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'ad54d92fffd34be59d7bcc45674cc4c3',
            'client_secret':'00b38f62bba94bf78c9a94b3325b22f6',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'69b5b6c4706346bdb9dd41f549a0c237',
            'client_secret':'0f30de99c0be49afb56050d29a1464ec',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'cb223156f7804daab8236cfa870660c2',
            'client_secret':'be59aea7ef824a75807af289dfed5da2',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'ristitulto@gufum.com': [
        {
            'client_id':'29a47c76a7654956a2e708b9420be712',
            'client_secret':'8604782495014693a1f32db6c26b30b2',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'653074ab87a6479da99cf0b2894739b1',
            'client_secret':'b0245bc057bb45a2bdfc2c27a262d628',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'1ab353d366064a1bb257960b583c4d25',
            'client_secret':'1214c09d603542d495caaae362ae21ca',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'338b642735bd4d1e8cc471d32df2eed8',
            'client_secret':'07d6de612246437f821a91749dd02a47',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'d83f41abdf6e424baea989f0f1712027',
            'client_secret':'67830b85364c43d0a205067e53ebc5d1',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'dofyodulmi@gufum.com': [
        {
            'client_id':'81d38e39a5d84a0ebcf9389db9709747',
            'client_secret':'7de809ac352341f89cc639c211df1ea9',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'51b24220ff664d1bb6fae6d40a2a9e74',
            'client_secret':'10c4c376ac9640a18afa90ccd10ea987',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'d497117e8e0042329f147e59d44e467b',
            'client_secret':'a003d3a9cef9481ca5a99746910b4dc4',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'13e8a5f170d342849fa1de281f5b8ac5',
            'client_secret':'4a3bc20079d84ea0af92a43f3d5e2f28',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'2dd46cd2d49e4382b52616e8f62294e0',
            'client_secret':'3fe7563c194a41ef836463ca5f78c583',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'ritrokitro@gufum.com': [
        {
            'client_id':'ecc5459a3e5846ad98f5664e19a09f4b',
            'client_secret':'cd92c71b212e42ef944c12856a4b1ea1',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'63898f24484b47739354a236b9215ae9',
            'client_secret':'140e9cd8430946bfac6812ef621492a2',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'9867454840c54b619d47f9c73dec0682',
            'client_secret':'1a4f45dc85734c969f2358a6a5ea4fef',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'5c9f4435ea5d4760ae5980da79fd20ef',
            'client_secret':'1c5a358cc4d94b9f96ee57e06203cdd9',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'00570d3da4ab41b99370734d33f21dc3',
            'client_secret':'da0f29f306ae4c0b8a854f84c8657717',
            'redirect_uri':'https://www.google.com'
        }
    ]
}


def change_credentials():
    delete_cache()
    random_account, random_account_credentials = random.choice(list(credentials_dicts.items()))
    random_credentials = random.choice(random_account_credentials)
    #interact with the spotify API
    spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(**random_credentials, scope="playlist-modify-private user-read-recently-played"))
    print(f"ACCOUNT EMAIL: {random_account}")
    return spotify
