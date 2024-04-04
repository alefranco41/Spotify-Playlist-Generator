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
            'client_id':'42342781a4a24920ad9e2bdc6fadf7d8',
            'client_secret':'7cd3cea1117c44949230e0c5eae6f749',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'b348fdbb04354b4d97043b3a5ccaf9bd',
            'client_secret':'21c57025090542c69fc29b25a3ca2cf3',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'39c7d018efbc44e2ba4c415b287b1869',
            'client_secret':'80f021fbbc4043e394e41bb643f288bf',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'9cb9359fbbf54c40b3208420ceedfae2',
            'client_secret':'fee1e4637dac446880a2594225fd36f5',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'2a27a902ccdc45cda1b07c80d3b76028',
            'client_secret':'fbb746585a844fdd9108c2d37512bc68',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'minin11613@mnsaf.com': [
        {
            'client_id':'ba1de7c71184496ea93337b6c8353b52',
            'client_secret':'ce52a2f932554265a854ffe834fe23bb',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'446bb7ed351840d491a7dff33beb2fb7',
            'client_secret':'1c28c6da327b496a96be5c234234537f',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'d9a9a87b31f84f76b00d35f07c246c26',
            'client_secret':'9bf6cec23f1448d597d4fce3682766b8',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'ba457a691e824321aedd116cde7aff9f',
            'client_secret':'c94f9500687f4097a992c7c888964752',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'4d8fd2c7b1e042e38b58e61ff124205a',
            'client_secret':'3ff239b8953b487a84f6b6c4a39e9ffb',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'muydihispu@gufum.com': [
        {
            'client_id':'17fcaf36776047b78ea0aa270a8623bb',
            'client_secret':'97cc7d0a7afc40b7a14f6486466814f7',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'832bf6d3f98b480ebc232127280340ed',
            'client_secret':'502e6aa1c3694437b09f4966bd1517f9',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'3619d4a4c0d74ba08c6f89dfd46091b0',
            'client_secret':'6c397054d57d4bbe9f8f5d8a42a33b20',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'257ef042a4e644ff8443156c3f2ae159',
            'client_secret':'38f1405acbe649a9bd9d04b04ceb0d07',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'8a16ac82ec13485fa09ccd7068de605e',
            'client_secret':'7a708a4acb9545058b1c6cde1b19bc9f',
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
            'client_id':'',
            'client_secret':'',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'',
            'client_secret':'',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'',
            'client_secret':'',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'',
            'client_secret':'',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'',
            'client_secret':'',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'sugnehomle@gufum.com': [
        {
            'client_id':'',
            'client_secret':'',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'',
            'client_secret':'',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'',
            'client_secret':'',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'',
            'client_secret':'',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'',
            'client_secret':'',
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
