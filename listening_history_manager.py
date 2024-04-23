import pickle
from spotipy.oauth2 import SpotifyOAuth
import spotipy
from datetime import datetime, timedelta
import math
import random
import os
from custom_cache_handler import CustomCacheFileHandler
import pytz #convert Spotify's time zone to the current one
import csv
import json
from tzlocal import get_localzone #get current time zone
feature_names_to_remove = ["uri", "track_href", "analysis_url", "type", "duration_ms"] #track features not needed for clustering
feature_names_1 = ['Acousticness','Danceability','Energy','Instrumentalness','Key','Liveness','Loudness','Mode','Speechiness','Tempo','Time_signature','Valence','TrackID']
keys_ordering =  ['danceability', 'energy', 'key', 'loudness', 'mode', 'speechiness', 'acousticness', 'instrumentalness', 'liveness', 'valence', 'tempo', 'id', 'time_signature']

#convert the "StreamingHistory.json" file provided by the user in a list of dictionaries.
def csv_to_dict(csv_file):
    data = []
    try:
        if os.path.isdir(csv_file):
            for file in os.listdir(csv_file):
                file_path = os.path.join(csv_file, file)
                if os.path.isfile(file_path) and file_path.endswith(".json"):
                    with open(file_path, 'r') as file:
                        json_data = json.load(file)
                        for song_data in json_data:
                            data.append(song_data)
        else:
            with open(csv_file, 'r') as file:
                reader = csv.reader(file, delimiter=';')
                keys = next(reader)  
                for row in reader:
                    data.append(dict(zip(keys, row)))
    except Exception:
        data = []
        print(f"An error occurred while trying to load data from file {csv_file}.")
    else:
        if data:
            data = filter_listening_history_file(data)
            print(f"Succesfully filtered the listening history: {csv_file}")

    return data


def check_features(tracks, feature_names):
    all_features = True
    feature_list = []

    for track in tracks:
        features_track = {}
        for feature_name in feature_names:
            if feature_name == 'speechness':
                features_track['speechiness'] = track.get(feature_name, None)
                if not features_track['speechiness']:
                    all_features = False
                    break
            elif feature_name == 'TrackID':
                features_track['id'] = track.get(feature_name, None)
                if not features_track['id']:
                    all_features = False
                    break
            else:
                features_track[feature_name.lower()] = track.get(feature_name, None)
                if not features_track[feature_name.lower()]:
                    all_features = False
                    break

        if not all_features:
            feature_list = []
            break
        else:
            feature_list.append(features_track)

    return all_features, feature_list

#get the track features needed in the dynamic programming algorithm
def get_features(tracks, spotify):
    if isinstance(tracks[0], str):
        try:
            with open("data/all_features.bin", "rb") as file:
                all_features = pickle.load(file)
            
            feature_list = []
            for track in tracks:
                for feature in all_features:
                    if feature['id'] == track:
                        feature_list.append(feature)
                        break
            if len(feature_list) == len(tracks):
                return feature_list
        except Exception:
            pass
        
        ids = tracks
    else:
        all_features, feature_list = check_features(tracks, feature_names_1)
        if not all_features:
            if tracks[0].get('track', None):
                ids = [track['track']['id'] for track in tracks]
            elif tracks[0].get('TrackID', None):
                ids = [track['TrackID'] for track in tracks]
            else:
                ids = [track['id'] for track in tracks]
        else:
            feature_list = [{key: track[key] for key in keys_ordering} for track in feature_list]
            return feature_list
    
    if len(ids) > 50:
       sublists = [ids[i:i+50] for i in range(0, len(ids), 50)]
       features = [] 
       for sublist in sublists:
           features.extend(spotify.audio_features(tracks=sublist))
    else:
        features = spotify.audio_features(tracks=ids)
    feature_list = []
    for feature in features:
        if feature:
            track_features = feature.get('id', None)
            if track_features:
                final_features = dict(filter(lambda item: item[0] not in feature_names_to_remove, feature.items()))
                feature_list.append(final_features)

    return feature_list


def get_tracks(songs, timestamps, spotify):
    sublists = [songs[i:i+50] for i in range(0, len(songs), 50)]
    timestamp_sublists = [timestamps[i:i+50] for i in range(0, len(timestamps), 50)]

    songs = []
    for i,sublist in enumerate(sublists):
        while True:
            try:
                print(f"Retrieving song data for sublist #{i+1}/{len(sublists)}:")
                track_ids = [track['TrackID'] for track in sublist]
                tracks = spotify.tracks(track_ids)['tracks']
                if timestamp_sublists:
                    for j, track in enumerate(tracks):
                        track['endTime'] = timestamp_sublists[i][j]
                
                songs.extend(tracks)
                spotify = change_credentials()
            except Exception:
                spotify = change_credentials()
            else:
                break
    return songs


def compute_recently_played_songs(spotify):
    #try to load the accumulated listening history (spotify API only allows to retrieve the last 50 songs of the listening history)
    try:
        with open("data/recently_played_songs.bin", "rb") as file:
            recently_played_songs = pickle.load(file)
    except FileNotFoundError:
        recently_played_songs = {'items': []}

    existing_song_keys = set()
    for item in recently_played_songs['items']:
        timestamp = datetime.strptime(item['played_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
        timestamp = pytz.utc.localize(timestamp)
        timestamp = timestamp.astimezone(get_localzone())
        item['played_at'] = timestamp
        key = (item['track']['id'], item['played_at'])
        existing_song_keys.add(key)


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
            if item.get('date', None) and item.get('datetime', None):
                date_str = item['date']
                datetime_str = item['datetime']
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    date_obj = datetime.strptime(date_str, "%d/%m/%Y")

                time_obj = datetime.strptime(datetime_str, "%H:%M:%S").time()
                combined_datetime = datetime.combine(date_obj, time_obj)
                item['endTime'] = combined_datetime
                item['TrackID'] = item['track_id']
                item['artistName'] = item['artist_name']
                item['trackName'] = item['track_name']
            elif item.get('endTime', None):
                item['endTime'] = datetime.strptime(item['endTime'], "%Y-%m-%d %H:%M")
                item['endTime'] = item['endTime'] - timedelta(milliseconds=int(item['msPlayed']))
            elif item.get('ts', None):
                timestamp = datetime.fromisoformat(item['ts'].rstrip('Z'))
                timestamp = pytz.utc.localize(timestamp)
                timestamp = timestamp.astimezone(get_localzone())
                item['endTime'] = timestamp
                item['TrackID'] = item['spotify_track_uri'].split(':')[-1]
            valid_items.append(item)
        except Exception:
            csv_data.remove(item)
    
    recently_played_songs = sorted(valid_items, key=lambda x: x['endTime'], reverse=True)
    unique_songs = [recently_played_songs[0]]

    for i in range(1, len(recently_played_songs)):
        current_song = recently_played_songs[i]
        previous_song = recently_played_songs[i - 1]
        
        listen_percentage = 0
        seconds_listened = 0
        try:
            listen_percentage = math.floor(100 * (int(current_song['msPlayed']) / int(current_song['msDuration'])))
        except KeyError:
            seconds_listened = (previous_song['endTime'] - current_song['endTime']).total_seconds()
        if current_song['TrackID'] != previous_song['TrackID'] and (listen_percentage >= 50 or seconds_listened >= 30):
            unique_songs.append(current_song)

    recently_played_songs = unique_songs
    return recently_played_songs

#Spotify application credentials
credentials_dicts = {
    'nignebotro@gufum.com': [
        {
            'client_id':'9d62fabb415c4acb8bf0ce9d2012f0ed',
            'client_secret':'7b4b7ebf1e3e4b87ae74ca86d295a109',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'552bd384190241f6be465fba62958584',
            'client_secret':'8856fade04f04e7b9afd04b3ccf4a5f8',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'c06d6c2e484847c1bd7f87a36d06af27',
            'client_secret':'bfef3b193c4240a9867d5029dea3ec52',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'32459636d0224002b3fd2a218c70f6cb',
            'client_secret':'1e6ddd7e26f14872ab3bdaa6c71ed7d7',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'a2728620554d41f28f89d83464f40568',
            'client_secret':'50efcac4ddd34b199e17eb0f284309c7',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'minin11613@mnsaf.com': [
        {
            'client_id':'007f100ccec7499e893a79d2f52daf49',
            'client_secret':'c4d9b12f72ea45aea2a2580fc10e62f5',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'fc8a585f120149a489ad064228a3f2f2',
            'client_secret':'8777e71a2732465785c25482d54d62f7',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'a446f7bd71744214a246abfd8ed98a70',
            'client_secret':'360ddc5d2ea3408e85d3360d09bfc598',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'3d32ae4a3d3b45d6bbbc5a128b37a9af',
            'client_secret':'f0045935b87141cfb7d9eab2ad466e2b',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'40b31a065f944292881e237d5680781f',
            'client_secret':'c1ef3231b08443c79db933d3f8166a65',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'muydihispu@gufum.com': [
        {
            'client_id':'c8afc2f6901f41f0877d6374efda873b',
            'client_secret':'4d77fa6ed3c2411eb45ef04a31b37f8c',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'2b40a2cfd4e94c6da2142f312b8763b1',
            'client_secret':'87099b74baf147f6b7dd652d234d636d',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'0bb713ee0cde4568aa7b9c0bf459f165',
            'client_secret':'5673d3a0ac034ad1b41d8f232817c0ab',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'d03a9d00752f41d18c0d054e7d98ff76',
            'client_secret':'e533893f1ddb4d1592026f3fc68323b6',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'7abc15cb1ab54848baf48861d1b42ee2',
            'client_secret':'4604cc8214424548ba9856cc3f6ec8f0',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'alessandro.franceschini.2002@gmail.com': [
        {
            'client_id':'a4bd7c65993740ecaeec5332dba20dcd',
            'client_secret':'6aa12d4dc2234f3089d4f356e4138aa3',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'172f44501fcb4d8dad500a09c3abb636',
            'client_secret':'95cbd842ac784dff84fe3ff6616e828f',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'e96d9d3571294a529add13efb8786a4b',
            'client_secret':'172c6f294f614f3f8bd777678db1eaa2',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'f0f0c1bdb5cb400991b4cc44996ab289',
            'client_secret':'2767fe8fd612450599278f7758e14399',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'8c5742f6d059418d8adead8705d8e24c',
            'client_secret':'db729bbe8109466c86c886335d8b0ff3',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'difyekilmu@gufum.com': [
        {
            'client_id':'633e1de56ab84617af1e152fc34b40d5',
            'client_secret':'84a1ad24cb5b4ccc988f873e0c38f461',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'1f5b9af30e6a49a49fb098c2e3e585d7',
            'client_secret':'29de0cd2eee14892acc4bbbcaac911a5',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'2dcab326b844489ba8ef811b06edf78e',
            'client_secret':'80707abba1b74fd7a16666a61d719c03',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'8a4c2beee6ca471794344d5e86083e0c',
            'client_secret':'020f990fbf614acead08082cfd6c8586',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'6ef3a7edf1014075996000b83e935bf4',
            'client_secret':'3505d76c2f0440e3ab31ce5bf7f1f0f7',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'sugnehomle@gufum.com': [
        {
            'client_id':'bda1b749cd5a479ea17d2af261e3b03b',
            'client_secret':'f37c24c948674177a7dc69bf0cb555a5',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'6a53502269e247cca9ad9267de93305c',
            'client_secret':'4047c273f59a4be1acd8d454004163a9',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'887eb5928c0146b3ae441946cac55d5d',
            'client_secret':'21dd50ba2769488380762aea27ba5d3b',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'c60ab67926464bbdaaaac0d6e29968ab',
            'client_secret':'dd11582b91b443c6a6adefbd788ad8a5',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'036fb15578744abc9cc08c940e373e6b',
            'client_secret':'f88197982a724e959507e0631a4aed6e',
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
            'client_id':'cba0f433cdba446283211c455fa6c99a',
            'client_secret':'1975a1cc7b8345f7b5dd43696256307e',
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
            'client_id':'4d7730df714742beac17310640307272',
            'client_secret':'fd133e91be384de597aa585d5c183cd7',
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
            'client_id':'3fb3824588b743399cdbead1395cdc98',
            'client_secret':'fe2e5ba688974bdb88f9efd90f2b9276',
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
    ],
    'nopsimumlo@gufum.com': [
        {
            'client_id':'467eca8433764e2398f594ca20d8fa01',
            'client_secret':'0e1558dbff004fc59abfffcb71ab282e',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'beec33b30dee4221ae5c49436bf7af17',
            'client_secret':'0895decf8e3d45d68d93370c763bdb78',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'dbf3fd46d1534c58a29700b48ade9a30',
            'client_secret':'a04a1ccfe696416695cc33c4e52d7b44',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'3d72f895691a42a697912f210b7d66ba',
            'client_secret':'72c881a6438240dd84988d58185cf482',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'6be3db7b32b74dd4acca57b30c6088ad',
            'client_secret':'aec64ee5c2cb488895ca0ee9be1a23d1',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'kerkeyakni@gufum.com': [
        {
            'client_id':'8abd08c675f946bdbc1dbfedc4d8074e',
            'client_secret':'988efa6a5e1f4b48ac0c2489f43d2fa5',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'94c67547a8c343168850bee5c254f24b',
            'client_secret':'77bb0b43494f4803a6f9f3a7f0884db9',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'09abb70c62fa47cd836b48c9389f39b4',
            'client_secret':'e4b36b04f5fb45c78e4af4476ee530e9',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'70246fb1350a4c819f99c2ceec471852',
            'client_secret':'2c638216077c40a19aebbb87939f346c',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'83c488cf1e3a4c3dab8bb0e3282ccd8b',
            'client_secret':'a3225f93513d4a90bc3d33f027f07a90',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'peltojotri@gufum.com': [
        {
            'client_id':'0af1254be19d44a79667a37386e2e2da',
            'client_secret':'ec574e5c76c34a54b23adc57c5fd6548',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'811dae79d4034a1c8a9ca982c8dff487',
            'client_secret':'7a0abbb0b4dd404096a0948618ab94f0',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'af7935bc5ca9487bbfe8c336fd65b8fb',
            'client_secret':'cb3e9e1b774941b5b986bf7b3da709f5',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'c020519a2e8e43f888d2d15763d1c48b',
            'client_secret':'f1ed2eb587174b608d5f536e5d0aa7ae',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'cb1a2e639e9e4e269e464c49f086997a',
            'client_secret':'4e4d55e26e6d4c788a5926604dc5659b',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'fafyohugna@gufum.com': [
        {
            'client_id':'0a36f742923e48ed80c8af1c3a3ab068',
            'client_secret':'83dec8ac75144a5b90e1c5e954df317a',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'56b372ba40394bbc9a17e2763a11fd50',
            'client_secret':'9811f1463eda47349ed199e4adb6b786',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'0bb48b54a4ac432ebc67a20573c87e94',
            'client_secret':'c84d1748bf694a1aa69507f27aa2028c',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'f4feef8795e144e99534c0b1441005a7',
            'client_secret':'f7f5489889464c6fab34a3401dcad6a2',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'c82aa805082947eaac89e6d124ec0ba3',
            'client_secret':'4eaa5a7d070d4784968fd90d795172fe',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'zerkitiyda@gufum.com': [
        {
            'client_id':'ecad528ea90940f8acb132def344554a',
            'client_secret':'9beff6cc1b10427dba3531754ca88c77',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'7899052b3e184b73b8a30000c7d42cc6',
            'client_secret':'c52eaf5708e4450f9f2e6c06449a0897',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'afa8483a7fbd411c9277b144cde92d30',
            'client_secret':'5626e98aa7a349298c7144b85d97594c',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'d6221ad1f5ae42ab98db5eef339196b0',
            'client_secret':'e8009953adac4b8b9bf2c8f13351d1c6',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'02b14fefe64b4843881a7af385397fbc',
            'client_secret':'563d0d2d7cc344e285767d9b22cd4e13',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'rapsijifyu@gufum.com': [
        {
            'client_id':'6b082062df024fe19b7bed1324ca65da',
            'client_secret':'33f3e0d797d04570a09ed91349b2e3fa',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'cccf64cc4c88470b816236d94dc68f5c',
            'client_secret':'de3d6282b2b74cfe82e02a775eb29783',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'918135a0ce6142908eb825476405b340',
            'client_secret':'ca9c5154df894803b9aec997083f1be8',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'7d7f9a79e1f24420a61298a88e52095b',
            'client_secret':'ff894168b7654ba892408330b4317895',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'1bcc4dbb1aaf47c297d20e08e2582a9d',
            'client_secret':'db753a3699974b21b3fde62c4dc7c254',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'torkagamla@gufum.com': [
        {
            'client_id':'9fb09c3da41d40eeb4b4f7272456fd6e',
            'client_secret':'2b0120047d7a45f08896f810ee652053',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'df260494f7634ef0bb4bfba12f642d1a',
            'client_secret':'7ecf92f7399044bf9aa2ff18c8ca4c19',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'9ec5fb43a2cc4a45a3dfc2e4da591715',
            'client_secret':'6a4eeed03aff4737a2c795d91b0f427a',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'cb432355267d4286879ee8275935631d',
            'client_secret':'1128a455c2bc4558aa719354bf53b7b3',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'e7e74514f2734776ab24bcc0e06160bb',
            'client_secret':'c274cc0f979649a1917197adb79dc5dd',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'ratrokelti@gufum.com': [
        {
            'client_id':'',
            'client_secret':'6e38b78580a741a7932c893cb831cd0e',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'5628971f5bac4d8e918d03fe5f815b3a',
            'client_secret':'7bba385ef3cf45f08a86e4621bfca74c',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'6cafe87e4ade49edb1bdf163cf7b881b',
            'client_secret':'3404db4e5bdd47679ca5e7047c6e5228',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'',
            'client_secret':'7961ae28c7b141e583789a03aff922a7',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'',
            'client_secret':'4f7883b408f3463983d43f4e6135d122',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'marziporda@gufum.com': [
        {
            'client_id':'0551ed667c8e47e19d83d93bd51d0c94',
            'client_secret':'bc2484cf4c1e47b798fc84ef1d835729',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'96a6d7423efd490782e80e260d48bf45',
            'client_secret':'71ad891b3291432bba4d0bbb65b4b047',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'c9c9b4ac75ba48d3b29b2df5fdfc10d3',
            'client_secret':'7d307eeb7a33417abc5ba072bbe50bbc',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'05878d5fdb4748948b4a00bca9af85fc',
            'client_secret':'85805a36cd874f64a8e753c610189f98',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'722fe71edfa340b38045df99f83c5291',
            'client_secret':'5a90f2ae8f4d409084b25b3a3a7adfbc',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'vudrehokki@gufum.com': [
        {
            'client_id':'b05659617bd94033bece515ada56f974',
            'client_secret':'f086ccb2cbc94b919b0311072766436f',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'ea7099a4ee454f338e41ee8bb529a5b4',
            'client_secret':'492590a97e354d4a81e3b0072903a5b1',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'208b1651d68846d99632523546b36cb4',
            'client_secret':'fc45a07d4b3642afbd74eba88ebe1bb2',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'6790eb42b71a4eb588e1dda4dbe4d1c5',
            'client_secret':'478b6676c2174fd5abf9079f74d3e54c',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'a2d5280d4eeb4fe8a102c75d361e1fc5',
            'client_secret':'5076fb9385ad426f8000405f27323249',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'nurdazekni@gufum.com': [
        {
            'client_id':'0a0e958b0ed04f5c9120fe3d0c6d323f',
            'client_secret':'0c0148321ebd494f8ec1faf7d23f2048',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'c593b205fc9a47939aa9d6b1f09ad81b',
            'client_secret':'b36e9ebf41864425afe0421943d3162a',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'1ad80dd9c30d4932919a3eb654061122',
            'client_secret':'19b05f62eff64b7881280142430dde73',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'fcaa954dd0f947e4bc405eeae7a8c8ff',
            'client_secret':'65516920757c4c179acdf1940cc367d4',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'e9534d3b72834be489b5e8ac2535fa05',
            'client_secret':'cc56a7fc2b5c4fc2b264f6dd82d696ae',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'daknusispi@gufum.com': [
        {
            'client_id':'187666f0a8484815ae5e4902a8611088',
            'client_secret':'ad351faf88a44f70ab9b8834bba3f77b',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'fbfc534515d442568a9e1e00be0177f0',
            'client_secret':'df46e5301a9c4f9f82afc6a9d6da4130',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'7618be6db7aa4fde8977e154721b1e31',
            'client_secret':'cab3f994154444398367fc63c67eaa25',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'04eb86c2123945f29116447f57946205',
            'client_secret':'ba55fb3c26e94e0db0fe841deb3959c7',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'d995a4ddc02c4da1a91ce4ea166bdb01',
            'client_secret':'e0b5e266dbaa42c3a8ab75966ee6d8a1',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'taydatelti@gufum.com': [
        {
            'client_id':'8f1a821defba466e963e2f953cc9f0ee',
            'client_secret':'e56cb66e48f14255a9a7935b995483d0',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'c657c6877d6c4e2697c6fb2605785628',
            'client_secret':'59421268df9a49da9c9a4aae1c3f87b8',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'11512ef55371480984887f9b7d75c7b9',
            'client_secret':'1aee1b25afa8499c9e0455dadae16e45',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'9114ac2c2b8743898e3d37c07cf00f60',
            'client_secret':'ec30a6b5103145d1b21b0e72ebc4a387',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'af392f6bb620426c86e1725e5bce46d3',
            'client_secret':'c46e898310924930b7d5fe1d53550a9b',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'kospunotru@gufum.com': [
        {
            'client_id':'bcd9bc2c3639405faccf0a2d55648099',
            'client_secret':'b38962951c18498c98f859bd0febcec6',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'8e5904feb85c47a3a8b0a3a580f954bb',
            'client_secret':'0ece4a4f94ad4ceca4f24fa5eaa02cf9',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'b389f447db4b461e9e23a3d928bf1e9b',
            'client_secret':'56cecf3b0ab34f439f73562ac6b02655',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'d76fc2864c0b428599ea7d05116a5640',
            'client_secret':'79e22fc03d9d4d8a937c5a30ecd27b4d',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'64a3a3dc93564cad9c35202154cc4231',
            'client_secret':'ac8bc34689d74c5cbb8575abdff8d7e1',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'lakkitedru@gufum.com': [
        {
            'client_id':'bf8ffa417b2c4e71944cf3cc4815732c',
            'client_secret':'24ca6dd135504e789e8b550eaf2fef96',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'5f925dda32a948309a87f0bc8c1cbce3',
            'client_secret':'c3bc79613dbf406ea30306cdd98e0b3a',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'f5001f89845b45fea1ed4891c7b2fbd6',
            'client_secret':'f4cd1312b3f14028b86e08f63156a229',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'b28694877f4f4b3f8b34aa62b7a04487',
            'client_secret':'503f186ab1e643d5a25a853135a0753c',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'cdb1eabde97e4d208e725d82632f06ae',
            'client_secret':'b1fea6c459414ac3a8140b84557e4354',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'gospavekni@gufum.com': [
        {
            'client_id':'1d66db8f96744a5c9a47033d6a97a08d',
            'client_secret':'ec05207e4e6344f590abde7fe89c6da4',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'d897fa6d293a419db2f245d2d91fc489',
            'client_secret':'1212647e613f40508b2a66655ddb2dc9',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'5ccefa23cf8b4ee6ae26a6ac583658c0',
            'client_secret':'dbb2b881dadf4c4ea396c44aeb86e826',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'9fc509de8d384b4da5fd33eb69abf542',
            'client_secret':'0139864437894bec90095caf2269b402',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'10a9944200184b2a860b97c1d5dbcfe9',
            'client_secret':'8c29834d1d4e4affbae5a97d94e4c1b6',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'zorkarefyo@gufum.com': [
        {
            'client_id':'cb72f2c2ed4f4ce88b7d4ecf7c135ebf',
            'client_secret':'f985a077697d4e2abbd24fb4bfc03c28',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'241dbf25aef7430ab373ae38695b6047',
            'client_secret':'13d35082a19440fbad724fa619f208bb',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'60cafcf71a014d87b7203a326110c0af',
            'client_secret':'63c0b61e5b4b4746b9aec6d548c78fa0',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'5bd4f6c295af445e826929d3ed50d084',
            'client_secret':'9dac7cd51f894b71b5b02ca698f4d69d',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'6e9bf87b3e464957988df94f8f1ce881',
            'client_secret':'ab5d07019b0b4dda844bd96822edb679',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'bolmiyosti@gufum.com': [
        {
            'client_id':'6a1ea780ce76439883ce088cb5a938f9',
            'client_secret':'7ec840223eaf46178a272c5d72a35b82',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'c34e44bc8fd1424cbed8241500b7ad54',
            'client_secret':'5ad975ca24694eae844b8d597bc785f9',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'5674cb45e89c4042ad3fb46e0d223c17',
            'client_secret':'e80c8b4aed6345f7a865e46ec4d16186',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'dd1ecc122ad84d4aa9b7484d704b678b',
            'client_secret':'a3614d92a30f4310b98a5905d6a0d2dd',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'d588c6f4faac465b96a251e434f7c2c0',
            'client_secret':'46d71e28fada4a1198fd15bc4264a3e5',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'yepsodipse@gufum.com': [
        {
            'client_id':'624543c2ea484972b75e456f9417240b',
            'client_secret':'0f867f298f524ef898c55f665b99e50c',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'63615718870b4a37ac43a0374e9ef2c4',
            'client_secret':'c5cb502e1ea34b5181893ffb512e41e4',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'8187d36d03b241618399521fd88224f5',
            'client_secret':'da4bd6df83df47a38bac5e108055e65f',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'ff47021bed3146dd9806661073039b0f',
            'client_secret':'9e9844dd1c5b4692a7605c125e446447',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'91997ee34e684b86b985375d5b1692a4',
            'client_secret':'e05e68e3fe594fca8babfc436959a5df',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'yeyditekki@gufum.com': [
        {
            'client_id':'1559845de925498eb471605c6c3ccd0e',
            'client_secret':'4ebdcc5266ee4307915f895cb60bcf5d',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'4ad7901241a04ea1bfd5842ff5bd58e0',
            'client_secret':'985cd67d365f4a26aa783174fa0da0bd',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'e63b5ece606147abb0452362895865f9',
            'client_secret':'ae8210655e674a38bcf979eba746507a',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'b7c924dba7144887aafedcc994d2faa5',
            'client_secret':'1769f2fdaad249b2806743d210e93ed5',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'21dbc11fb6e0481ebec4caf30003ac49',
            'client_secret':'701095cca8a54dc0bcb9887e3f9b7467',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'faydeharta@gufum.com': [
        {
            'client_id':'eaf88dba7b274083929f8a660b4a9384',
            'client_secret':'c93b3400cb0c4896a770677185b015cc',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'929b33d027bc45dfb2e1359100b5da04',
            'client_secret':'a6de0396478d4ef6a2ffc0618c9f4e43',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'85cb9acca4c1415d85ab29572ab50d01',
            'client_secret':'bf583ea75d634ebfbdac6e20e7eaf29d',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'7d8ae706e93b456a9ba3ea2c3b8ab3ce',
            'client_secret':'24dfaf5376424567a7bbd0d0dbeab07a',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'8912594caf034e8699cf8e1bff8823c5',
            'client_secret':'d55b27bde46a43c3a04feb2ba5a90857',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'viydogispe@gufum.com': [
        {
            'client_id':'0b586f70b2964b04ab39cfda5c95bf0d',
            'client_secret':'e9a3309c0fe242a9ad0394b6cc032c43',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'6ac1a2c3e87d42b0ad42568f1a8070e3',
            'client_secret':'d8ca8bf2435245ab88e1d18223b1ea72',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'',
            'client_secret':'a107ac58d524487aa3aba806cd4477a7',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'264712c37a70403dbf902e1c54094664',
            'client_secret':'9c6c8b64162e4eebb29aa8b5b60544eb',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'c5986ffbd0a94e739fc729d50bd41704',
            'client_secret':'39d2da7efbd6415c99fe8879305cc78d',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'talmotuyda@gufum.com': [
        {
            'client_id':'03ea58d01bb944d3bb1ad33bddfc973f',
            'client_secret':'fc50177499a64df1b67bcbb1535b1a48',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'c30a869f5ff24d9caecc00770ab93013',
            'client_secret':'bd8d0cd772d44423a9828cf865c3cab1',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'3f2d1ed059cd45ccbdf3e94f8970cf93',
            'client_secret':'1a7c85ec0b214955a620bde64e358d40',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'6010c7cc6317485c9acb7e43c12be4bf',
            'client_secret':'0d91010ec68c484b9898eb9dd0c458b4',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'e24078f758bc4448a777a6acaf13b9bd',
            'client_secret':'c3159d28bb504ab3a501cf4f5b30cb62',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'dutrikeydu@gufum.com': [
        {
            'client_id':'a4c1cba798164a93954e996699afd217',
            'client_secret':'04bc4027eba443fca2c211923f35037f',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'607e334ea1de4f2b86c6d70a09bcb122',
            'client_secret':'b0262c5b4e714cd38c73954cd751e48c',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'6274f04b15f94f2988449554155b1810',
            'client_secret':'b3f94951f6294a60857e9df3e1e03769',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'84317a4bd70f41cca6511b94f1c165c9',
            'client_secret':'cfc7bf24b10544a5b27a01ac19905ff7',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'aa50a9df9b2c46088f52174dae8868e0',
            'client_secret':'7806d074e8d7472a95fc5b912d1655a3',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'keydametro@gufum.com': [
        {
            'client_id':'3fd8e6b68437449392e9fa0002eb79d2',
            'client_secret':'2aed2f43580d4073807ff9e69354c293',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'757d3d3e74964169830cb4f35ff6a7c2',
            'client_secret':'4e9d2335a0ad423eb450f4e821907514',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'f98d738d8c3c4c48afa59c3fb0fe9bc5',
            'client_secret':'48c94ad1c0eb4f96be25a408e12381fb',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'38b2591c6aa44054b7d1db916e281963',
            'client_secret':'4dd38af2b3a9432eb528901060b99285',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'f61aec1a025c46afbede39a13a9e3505',
            'client_secret':'e30ee0efcac04a6e883a207bde3520fe',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'zatragimle@gufum.com': [
        {
            'client_id':'5ca89b1a94d840809b2fc4212e7e3c93',
            'client_secret':'36bc2b29b9664e308b7a69b8edc35b6a',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'a8f959d58663417bb6f2ea0d88f9d108',
            'client_secret':'3f944feb9ec44e96bfe4f869a3b82196',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'d91b33629ff542e8bf18962c13d1e140',
            'client_secret':'31a6987a878e4c0e85a2e0c144ee7566',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'c2e77d9bc4ff4a0da3f5545670390dc4',
            'client_secret':'06bace3aa6c54752ab3381b3c6241af8',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'786e3814cbaa42f3ad7addd1b7d1c9af',
            'client_secret':'c3b1a67a65ed4ba39a178716998b3c2a',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'zipsedospa@gufum.com': [
        {
            'client_id':'d12832e228a74e95a9688328a567d4fc',
            'client_secret':'08b8d3d2ebd84a33b7f9c8a798f2c401',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'bba4b73a077947ce9c5862c6414bdf1f',
            'client_secret':'b23389fc7f2e41778082155724b285e3',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'a64545715c1b4b698ff7aa09167f71f0',
            'client_secret':'6d5d05203e1a4bc8b060b9371993c2ee',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'3c8c3d06c55e4be1ae47ed243c8c2ed9',
            'client_secret':'983de8fe18d842b5817e0248a6c4ee1a',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'6e9de4a68b904b9594dafa72040ef8b0',
            'client_secret':'64f135f37d4545a2962d0411c137d04a',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'neknuceydi@gufum.com': [
        {
            'client_id':'e76d90e9e8194b8f8372936117a2fc76',
            'client_secret':'b232ff3da6b14de1a261b017dbb2ec49',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'ffb3bb498a9a4c5f94b6b5e442b7257e',
            'client_secret':'3ea78854044648bea568557369678ed9',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'8267c67a511543cd8adeacaaf31a2ac9',
            'client_secret':'59999cc199c345f199e2b4a0243f030e',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'88b0b2281b10472d9b82937247d024d1',
            'client_secret':'137e780b293d404fba1b8d01054f3bf1',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'3ec57acc9da5436ab8d15ddbe26d0611',
            'client_secret':'d61fdde7ad7d47c99e11be7e728dd03c',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'gotrokagni@gufum.com': [
        {
            'client_id':'92f1489cfa604bc2be3bd3de99de5fce',
            'client_secret':'d9faa0ac46df49958f678553f592a90e',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'966795f958944453b5fbd1cf3566f02b',
            'client_secret':'3ea2b3d524e54dfda81c4150ec655907',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'f8ec3b4d650f45d0b847ef9789ed9b24',
            'client_secret':'5709bd48b5654c0ab8044ad8ae788787',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'207c70d881e645c197eec80d8cf00534',
            'client_secret':'91ece84f7a934f7e9fe276ee7c670b0a',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'7700878d9bcf4241ab4720f1a1f968ef',
            'client_secret':'9090d54dedf847958eb8a449ec0ebb45',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'zafyeyoyda@gufum.com': [
        {
            'client_id':'b120368347eb428ca86d3b308693b6f2',
            'client_secret':'5a53768870cc48c6a494a42935f0c748',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'6a6e8a1064ca4c9bb832a63b7128b2e0',
            'client_secret':'6109b0da1827437e80de9bcf3f28f056',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'db4e8400f53a47faa89e72a1097b04bf',
            'client_secret':'0bea6ba87c3445109c671635c7d1502b',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'20fa8d86c0d24dcf80c750580108fa99',
            'client_secret':'688e96c1bf284dbe835e3b5d098a2be4',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'13d0175d400a44ef9dca95be63abfaae',
            'client_secret':'587e08724f3d499db1d2fc24101d4556',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'vaydodagno@gufum.com': [
        {
            'client_id':'8ae4a98788b545c290dab17502f813bb',
            'client_secret':'a8848cf588b14007b245f4243d683352',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'246b0e85a2a84f44964216ee41e21e0d',
            'client_secret':'018eede61d234dad95c5a0c65d5b23dc',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'5519001b8a6e4d8f8f1d2d9b207824cd',
            'client_secret':'bf378ccac7134e898cfa05f5a6dfeacc',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'349e730e64f3479f84d3c0860e0c0e20',
            'client_secret':'f8b59330af054ced8572074ca5ad73f0',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'0484cb8e640344c5aad3c5427de8b9d3',
            'client_secret':'d3d9f9efdbb843189f7172f3ad7c0059',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'gemlotafye@gufum.com': [
        {
            'client_id':'5abdd9b0bf254b5da735f24161e3911a',
            'client_secret':'360a8b21d1654149a6714fa8c8ecdf5a',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'e168b7cab93849069b61e3ad05c9fe16',
            'client_secret':'7b7e58cd73aa4144a7cae0058901fb3a',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'de36b3587f034fb49887585cdb2ac14b',
            'client_secret':'d0f0c127839c45148d54fabc66f43d68',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'57bbed8eb3454b6b8c622f9fdea84f6e',
            'client_secret':'49c99566971a42deb1799854de701764',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'fc68e38ec545475095c7b243ad4eb993',
            'client_secret':'2fbf068a32cc4570a2867f4f92d38a34',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'yorkenifyu@gufum.com': [
        {
            'client_id':'c2e97c3d55f54785b8c5e7c90d295738',
            'client_secret':'e5467edc586347f29293bdc6c58b8f04',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'045c631bf9d44362915ef9c8241e899e',
            'client_secret':'6471b90ac34a478491ea9d5b20a7947a',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'0fc4b5a16c44445081e707d451859368',
            'client_secret':'b37bc984288e421391eb3020e3f8a9a8',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'ef3e59f81eb045b6ba20a881ab836a6b',
            'client_secret':'8b96d0ccdf9342fdaeec117922c64a80',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'e8aca0d801e149f5ae18aedcffb64bf8',
            'client_secret':'b12e455bf91f46a5b61f7235fcd7567e',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'rulmupefyu@gufum.com': [
        {
            'client_id':'c3c241c5d7a64cfe82709c9951dd6e05',
            'client_secret':'8e096e444990482f80ce1cff721e446e',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'ff9107715eed4bb7a69b97fe1ad33ac7',
            'client_secret':'f11f329c25324fd782a880a7a5442be8',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'0155dee444dc445cb6b490620bcc3fcc',
            'client_secret':'6ff4da2deac24cf1ae8f7d22d4893c01',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'35153339d1fb4e25badd3ef1ce9589a4',
            'client_secret':'1958bf74dc7241558af2ff174d4d772d',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'374968e436cb483198720cda08c4cc75',
            'client_secret':'bf2f84dd7f50496e92fdef2b1e8ded2e',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'catrohafye@gufum.com': [
        {
            'client_id':'592304aa1df347cba0657f368fffb455',
            'client_secret':'3db94811d7da4f3a99124b9c1874c074',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'23c01ee55be64075ad89a02e9a12dee8',
            'client_secret':'d09ca6bb4bc04432bed522488236185d',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'81394151d5f74416be7abef25fabce1a',
            'client_secret':'2611422ad5a549688688c4103062753c',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'0ba85a233de7425ba69a934461b43244',
            'client_secret':'1b2343a9506a4ecc93e8ab9a50988f12',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'b08d267172a641078907c57f9c537307',
            'client_secret':'f167b28f112e491392ebaec39149f23c',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'zitrayimla@gufum.com': [
        {
            'client_id':'bb8f56df5fba47298256e008f0f5c0ff',
            'client_secret':'4e1233501d4846d281e1a5cc585c1cbb',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'cdeb911f7d364359b25f268d3edeeaf6',
            'client_secret':'11fd490edc2b4d4a9ca7aeda23a8c4da',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'ab54c6563ece4311a4aa5203f98eb647',
            'client_secret':'07045275764b47008528bee28905e17b',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'25df2cfd8c754cc1913b7c9d127f58a3',
            'client_secret':'7953c8dbb07f4de3b62d0002789a0032',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'7b56020cc89d42c89e558570f59832fd',
            'client_secret':'87b4617dd1c141c6ada312ea1d59ab94',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'gifyovadru@gufum.com': [
        {
            'client_id':'a4d4868d932e4f199ad6cad92c3c498f',
            'client_secret':'d766c88e87c9408ba87c6df1bea2a383',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'58de95bbac8c4d3a8c36061602b3e95f',
            'client_secret':'2484146ea27243ed95c33d2b0a40af8d',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'07ce1d54b76e45f881afb8625f9a0a9f',
            'client_secret':'a00d880d446b4c109ff2833b4047a667',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'cf84fd7fa0e9494ca5d87c4a80db855b',
            'client_secret':'632052cb9e704e2aa9e5029be90d3d71',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'8d4134ca1462466e82fd2cbdffde2b1f',
            'client_secret':'76d9d80e5aa74b7da64e35f117d88394',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'podrololta@gufum.com': [
        {
            'client_id':'5c7846b1fb8645fe84bb60b4565d5bce',
            'client_secret':'d6644561e7ac49c895a077f509b273dc',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'f0a0d2cccd3243a89251f9e4edc3f442',
            'client_secret':'3715b4a03ed046dcab0e548b35153e72',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'4d738a0842b7404c9890d3370ffbc23b',
            'client_secret':'92ae3e5032ac428c93dd68d11f07acdb',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'7e943fe361514702875e83fab3d709f8',
            'client_secret':'b9dfabf2deab40c1ad92e80b7a3c5056',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'9b67065fd69843be86caaa574586cdb1',
            'client_secret':'880b82e273084d83aa236cc4eba6b935',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'zignipamla@gufum.com': [
        {
            'client_id':'fa4914f3fe4847129da19882c8d7a764',
            'client_secret':'646dac346a5e4a669d709f135469393a',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'b1be29f61e3b4ffd9df7c7635b33a441',
            'client_secret':'854ba1aa89fe468dbf6e7776d057fc6b',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'c28dcbc18d5d485b9e730e02db1818ae',
            'client_secret':'d4f3891bc53448458cc860209674a579',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'5ad0bc7313f44b13a96791205beefd11',
            'client_secret':'021375bb07394c0ebd876609dd43d2cb',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'5d5b12bdf1e04d829b55418f362dacfd',
            'client_secret':'82ba8bac42a44b799f977ff568c649e7',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'jukkekerko@gufum.com': [
        {
            'client_id':'e2307ff9812b4ce6b509e8f94f3db6d1',
            'client_secret':'05e655cf301a40dd8775bd484cc0f5b4',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'fbb83e4af2334017a0898ba6ed5b85fb',
            'client_secret':'6a5241ff7d564db7a6dd86fcf8ae3999',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'b52432a8a2bf45ffa659935b98a9b95b',
            'client_secret':'576f72deda8446cbaa57545d641da575',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'6d6e7758f7fb47ef9564afb8118eb78e',
            'client_secret':'161e55ad8bb744f08e230735aa78e22d',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'8903c9d1960b441aabb49760df374e9b',
            'client_secret':'fbbf80469e2e48e2b9575862fa1d86ba',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'berdupulmi@gufum.com': [
        {
            'client_id':'e00457cadfd040ca8fb07d366199dd45',
            'client_secret':'418a41959c5a4ed6bbeb3cfa8f25cede',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'ae2403d4981c4c6c95f581066ad8b341',
            'client_secret':'dd451329dc094bb7b268f714b4f65e4e',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'a65c775ad6a744f5b205306100e1df59',
            'client_secret':'f91726697ddd49aeb6b9aee889223ff0',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'d7f51bf5e14c44b689df36639d4a1cbb',
            'client_secret':'e676e59cbc4940efa8386ae79ea9c25f',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'3171cb494c5b437f9bc35083ae9b66f2',
            'client_secret':'6f484d98611947499bea08e824b2a3d0',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'carticakku@gufum.com': [
        {
            'client_id':'d78f63fad043426291d1ca50692cabb0',
            'client_secret':'94990bceadd34b52b683a8882840d9ab',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'1c5a15a192714a5b9287c34e29bea169',
            'client_secret':'39d5a1d35d69493ab309b39bb042cea9',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'db59f83148b04a15ae65ba4af826fcfc',
            'client_secret':'cd740df0c2c1475eba2c2d28186f3635',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'d03ddcd3d127440080c93ec7eda6ac90',
            'client_secret':'9af0f1511b154a938ab4b12fc177d41e',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'497b10e90c264286a0cb55136eb7e88e',
            'client_secret':'9bc1bc38bbde4f4aa5589ba2bd69a0ae',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'didriyotra@gufum.com': [
        {
            'client_id':'53c785d580fa46a9b6809db44e3c2188',
            'client_secret':'179849ca13c44568bc11bd50c8b60d0f',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'55841177bd894fd8a52c65ceb3caf04a',
            'client_secret':'9e2f856d1b3049dfa62d0a04cd1eb040',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'f3460b15c5f44ef88bd286c3a02f9e41',
            'client_secret':'ab21d909731e4498b1cfa64da8d8ddd9',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'7c105d8b69204ea6a5516a65c416e110',
            'client_secret':'847288dc27104856a47a851edefeee44',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'7fe6cd3fdbef49528f15caeb4099b6db',
            'client_secret':'19627a4fcc8446cbbbe1d9a3ae9f90f9',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'zegnavurda@gufum.com': [
        {
            'client_id':'53d1a65feaef403f9faaf8595ea4fedd',
            'client_secret':'de5a79001371406db8b53ebc986deff8',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'81b969b175cc411a95f91f9fc1eb5f55',
            'client_secret':'38f17ed1bd6e432db099fca63659765d',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'6c8c700f1de94b239b5139bb8eb839bc',
            'client_secret':'2da40c12dad94f67a564d5985f498701',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'60199b1497794b919f660d97da9021ed',
            'client_secret':'94a66723781541fcbb9748fc8916b117',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'9fd145dcaa0f47288cb634be0a2cb83d',
            'client_secret':'4eea0d6060de4f189520ce4a88955d75',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'zokkafipsa@gufum.com': [
        {
            'client_id':'5bfa98e207ce4c8a976fb7c98a77a5c2',
            'client_secret':'6afa7a925b194ce786fc4816a009fcc9',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'adb010e1004b43b49260aefac343b90c',
            'client_secret':'f24172af33174959a34ab537e31ad360',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'33854dbe6af5411d9cc4c5ddfe77cd78',
            'client_secret':'f62ac9cb350149d9950473d515ac048a',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'50defd41994f4ad4a455a648d5235c49',
            'client_secret':'db52d73033f54babbdaeb218cf3c4e36',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'87dcd1c388524c03bc8f94771f487652',
            'client_secret':'ad59b9e8e82746149a4c7780f1e8bfd7',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'ramlozimlu@gufum.com': [
        {
            'client_id':'',
            'client_secret':'d2ec8821094a406b9fd02d6173c25ba1',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'',
            'client_secret':'a77ea50a9f214acf97e20502bd0f2de8',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'f4d1e4be36894c4b995afb8f3e4b45cc',
            'client_secret':'6dcc209edb9d4322928315badd643163',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'99ad661765b8485e82f3568421fefc66',
            'client_secret':'29272ea6ca7842879d4bcd60a0b583d8',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'2ff6c3df665546d6b875f669044821c0',
            'client_secret':'7126a4fae95f40f5a12f4601518066ef',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'jadrudukke@gufum.com': [
        {
            'client_id':'77e482aebcdb47a78b8fea00d4ef246c',
            'client_secret':'dc37c29789634f82bb1dbf18bcf090da',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'c8dc2605fd0e4244af57278c885a8df6',
            'client_secret':'c250b57ad1894086bc7a76ea19988219',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'d5ba67dee5e1486c8b334b8d9db0c3e5',
            'client_secret':'a3acd5fbef0a4176b1c3904cddc8779a',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'6ede402bf7714489a35f185ae0ea154a',
            'client_secret':'bca3f0fcbbc44f0e93381466dede801f',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'c0ca9f9f5de64065998f8bfe1425b77a',
            'client_secret':'63d4ad54bfd741fd95ce0cbac7ae990c',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'celtatirki@gufum.com': [
        {
            'client_id':'66004209bcf643ddbac34e255036f0c1',
            'client_secret':'3de05468ce254c129986df27f383ba48',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'88f116ac7089426592d94bc7c2c2798b',
            'client_secret':'f91df43be8d5482286bd43acfed7a752',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'77352e3f51d047129d2a40394bfa5105',
            'client_secret':'128f5480bfa249bd8df2ce0358741194',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'74416894341a43f98d880c1064faaced',
            'client_secret':'72b3cc2f9dde4e87a84024df5a8ff268',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'3f2df329f81e4532b7aa4999534e965b',
            'client_secret':'50361badcbfa41b9bdf55a24a86d1b17',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'kefyefospe@gufum.com': [
        {
            'client_id':'8818fa31d8494d37b491d4cd8395cfee',
            'client_secret':'3522b73a01474a3abd91156ecb5af6f7',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'3582ae2eba814e42abe2ad406fb2cd2e',
            'client_secret':'b59ce662eac646a797fef69a6dc9ec88',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'1fb3d9ba35e845b48e220510533cddda',
            'client_secret':'8eed783b716541a181073d7230092edc',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'3730d6333bb04d838aeb67a7ba5989ae',
            'client_secret':'5730715f26704e2b91ac0acfd9de13bf',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'ee39e714b7654b2790079ca323edb200',
            'client_secret':'a9868f60278d4162bd7447881f73d997',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'zugnalitri@gufum.com': [
        {
            'client_id':'33e59dffbf334206930b9321088ed2eb',
            'client_secret':'96952b9fa57d4c35836a1e6420f95244',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'e5f8e0dc84cc456588c6d62b08916889',
            'client_secret':'46c66d15a59c4a9fabf4851469240136',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'b5fa4f2cb56c4ad28a449fe1c4d4b397',
            'client_secret':'478ea14ce9b643ceae021aa917133244',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'0c05a8cb2716424c8cafa2b6cedbe5e2',
            'client_secret':'4036d834dfdb48bfba7f46968350dfe1',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'fe6e5d5a7e684ea695554893b5659447',
            'client_secret':'95f08031276847ee9119ee63efcec2f6',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'nadrazukno@gufum.com': [
        {
            'client_id':'',
            'client_secret':'68cc4f06512f450c9e3a9e3ffb021c11',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'037ef104eaea4eca8ea51afd384c5339',
            'client_secret':'92baafaee9294e9d8aecb5808098ea52',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'11a8fc7acd43426eb6d28dfaca310f25',
            'client_secret':'dc55549a808c43b3b3bcd6aac5ab6c51',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'2a0d85808e4046bcb2d5a656968a4fcb',
            'client_secret':'d1888c948b3945d2843822fb65ca0fc1',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'',
            'client_secret':'6c1be70115f3490ab98a52d11c7588ae',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'meknuzipse@gufum.com': [
        {
            'client_id':'c384764cda734b76a33b28d807123450',
            'client_secret':'795edb6269e94c6eb7380f3fc2eb69b8',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'c862c43218c54f27b5cb3cbb9bd01905',
            'client_secret':'eca414adca684f8b815db742fbe86373',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'6993c783cadd4d41aec5a911625bd50c',
            'client_secret':'b9cead61204d4b0bb9a178fc5de0b007',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'4c8c7ef1e8144a54ad0d949aa6812529',
            'client_secret':'00df43fa5b694f9eb50fb515c71699cd',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'9e87e6a053194048886a248bd70e3e86',
            'client_secret':'fa53177bd97046eba1b0ff0b6278ba8f',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'birtinosto@gufum.com': [
        {
            'client_id':'15d5be5137bd481796d3d8d6c1654d16',
            'client_secret':'bdbd96f24a024d698d13cec101ab86e8',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'665dfb8bb7984f02ada49885c20e5dac',
            'client_secret':'89e0fcad961c41199dde0ef7c37776af',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'a3a57e90239f45fbb50803766e0c3020',
            'client_secret':'da26d0e322ef43938c765a994251e135',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'be34e6eae9ae4f59a54faf8915560d14',
            'client_secret':'4da2a93a602f44ec9918c25283328658',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'ff4a1c6baca74d51a8533efdc67f8125',
            'client_secret':'2c39f0f49bc14e8abc9408698fdfaecb',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'cutrodolto@gufum.com': [
        {
            'client_id':'6c6f6d408527401ead15a290938618f0',
            'client_secret':'9f5b1a66651f442da3542d15e8340df9',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'49b999460c4341858c7113adb9d099f6',
            'client_secret':'5ef75932e3e04a8b9ac2d6ca72bd9fdf',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'a5c922e7d70e4dc3a8bea730b3a97949',
            'client_secret':'06ee48f627e04487baf80f6557c80348',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'8381068f3e2b4bfd9ecbbc018dcfc53a',
            'client_secret':'c02bac0906f94614ab0ded9f3f36398a',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'42c1aed176664abb8d9ac43aab556f01',
            'client_secret':'64cb54cf7f034469b5b44903b73bb3e9',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'zarzokasti@gufum.com': [
        {
            'client_id':'ae4318a8b9fc4029a0a1abd880eb8134',
            'client_secret':'5d3e17da32dc435b89ccb9762208a04e',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'95c4df9c3ec54a67960ed77157a058c3',
            'client_secret':'5a65256e5001410e8f1e434a7df3d7b2',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'227ed69b045c4de7b73c85ef638680d6',
            'client_secret':'ae42ba807fe240ac918567dfcb2ec57c',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'b5428b81c15c4a16be6289e6f155fbaa',
            'client_secret':'ec04b568e6f04ba19588db4fab2ba3ac',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'ae792f58d3a84e2eb748ba6aa73146e3',
            'client_secret':'c99cf220cc754fbdbfee1fb0273bc972',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'derzokelto@gufum.com': [
        {
            'client_id':'249c21bef3144a428b7c364d3f29645d',
            'client_secret':'f9b95527bb724d3397f9100c99cc4d79',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'ca1d042a3fea4a4e899967894b9a3a87',
            'client_secret':'00980402eee547249e266da5cc18b852',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'082c8942234c4a2da8f5f5962e1cbc92',
            'client_secret':'81fd39e534a54af88290f97269d187c6',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'611e8ca7dcc94a3baa4220ccda51e46c',
            'client_secret':'573fb5511130445ca076c02aaf4fcd04',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'773dc2b5ff0d4c2d9e716282f241d3f3',
            'client_secret':'6442535f03b44abeb4a0633584bd7798',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'dortisospo@gufum.com': [
        {
            'client_id':'fbfc11b0f1e1443e854b6620c831882e',
            'client_secret':'55e2f0ad26154515b674f65f6dd8a4d3',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'763b49fa0ea94f1cab540930cd35a5e9',
            'client_secret':'e196535bdf1d407792e5ad86fc1d5d05',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'9bcd91d9077647888deb015ed47d2e20',
            'client_secret':'6b4fe72467564c1bba55ad963097cab2',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'ec655945e6524f31a34af33236211fdf',
            'client_secret':'cf772a8d61294d698c55c726b4c2dca6',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'13ea4ab1920d4a569e5a88cbf6ecc2f4',
            'client_secret':'fe7c7a2a07304556927de2ccf5b2a89e',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'mardobolmo@gufum.com': [
        {
            'client_id':'9ed1fa2af55740ad9c79f1acbe348fad',
            'client_secret':'f78e1661cfd642cdba2bcacddaa3015c',
            'redirect_uri':'https://www.google.com'
        },
        {
            'client_id':'fc554f76e9f54c24b6e5205df9b6e19b',
            'client_secret':'a56e1a6877504bdf8bc9ca6af22a911f',
            'redirect_uri':'https://www.google.com'
        },
        {
            'client_id':'7e254cca63734d5fb4263630e46c9001',
            'client_secret':'68d098d187cf4a0e8c455a9a5e75e61a',
            'redirect_uri':'https://www.google.com'
        },
        {
            'client_id':'75dc3480f47944f6bd3945349424f1f4',
            'client_secret':'ced89367c64e46a99797668b52b49351',
            'redirect_uri':'https://www.google.com'
        },
        {
            'client_id':'da5738fc5b964cfaa86838eb0d52cfee',
            'client_secret':'21a390bf63804827a2e800e92ae96b13',
            'redirect_uri':'https://www.google.com'
        },
    ],
    'dotrogemlo@gufum.com': [
        {
            'client_id':'b353535fc5ac47f7a5e9266e49df3c20',
            'client_secret':'b47b71e6453d4200ba1e2964c3585961',
            'redirect_uri':'https://www.google.com'
        },
        {
            'client_id':'107ea80c9e95448ca8fc3b46597f4131',
            'client_secret':'1fce3dac48ca48f0adfc7fcf4c3f8caa',
            'redirect_uri':'https://www.google.com'
        },
        {
            'client_id':'08a267de2e3f49adb92a7db4a591e275',
            'client_secret':'1688897109be47df88edebce7b2f3c79',
            'redirect_uri':'https://www.google.com'
        },
        {
            'client_id':'0ccdc810b6a6405c944b99ce6b30419d',
            'client_secret':'de06df99f2994c438a2dc23f6ad9d151',
            'redirect_uri':'https://www.google.com'
        },
        {
            'client_id':'2f1923210e974feab528814ad1c686a1',
            'client_secret':'69cbb89772ea4860b8cb1601d8aba1dd',
            'redirect_uri':'https://www.google.com'
        },
    ],
    'hagnehepse@gufum.com': [
        {
            'client_id':'f0a28cabcc7845cca85fe743dd94622c',
            'client_secret':'464e27460eea4737848657ad80245380',
            'redirect_uri':'https://www.google.com'
        },
        {
            'client_id':'0384e1049ecb44b1a2fe8d218550d19f',
            'client_secret':'e2bc6d4774bd493ba5c39140be505273',
            'redirect_uri':'https://www.google.com'
        },
        {
            'client_id':'69337a9f9c4d4f1f925e2790c52c6e81',
            'client_secret':'6d83ea3faada49a293598201361ae46d',
            'redirect_uri':'https://www.google.com'
        },
        {
            'client_id':'31ccdbae7d1d4fac8d124cbf9547b1fb',
            'client_secret':'f3ec82f5d3664a8f85360c21819e326f',
            'redirect_uri':'https://www.google.com'
        },
        {
            'client_id':'0c2fefb53e834081a3f06f13ad3bb48a',
            'client_secret':'85f93ee75b9447eaa230c1f35c7778e1',
            'redirect_uri':'https://www.google.com'
        },
    ],
    'nirtitofyi@gufum.com': [
        {
            'client_id':'630ac7f0aa7947438f8c973a27f0ff1e',
            'client_secret':'fcd145cffbaa4d29b8dabb5dc89d2f38',
            'redirect_uri':'https://www.google.com'
        },
        {
            'client_id':'e2dd21b48264435b839aa374405e93cd',
            'client_secret':'84c7dea2eb4e40528334c7c948d7d4b4',
            'redirect_uri':'https://www.google.com'
        },
        {
            'client_id':'d749ba7b7e4d4a7f95f524f07b911ce0',
            'client_secret':'226edb4a08a54dd4bff810ad6667430c',
            'redirect_uri':'https://www.google.com'
        },
        {
            'client_id':'978b9b59b9424df2bb687b2f5fd86ae0',
            'client_secret':'f0326628c79342fcb75ea90201ff16b1',
            'redirect_uri':'https://www.google.com'
        },
        {
            'client_id':'b75be2e2fcd54c02924be1c67e9a444d',
            'client_secret':'d5db6fe83f94431f99aaba41a86561a5',
            'redirect_uri':'https://www.google.com'
        }
    ],
    'rirzocorku@gufum.com': [
        {
            'client_id':'0f34031d6cfc4472a71509b26adbe493',
            'client_secret':'c0c681ede9054a23afc3385f057f1bfe',
            'redirect_uri':'https://www.google.com'
        },
        {
            'client_id':'6929483ecd5e4239b95d5829ac758ac5',
            'client_secret':'6dabab9397374413ab78d48ba4fe42a0',
            'redirect_uri':'https://www.google.com'
        },
        {
            'client_id':'f98369657cb648ab924e6ebcd4416f97',
            'client_secret':'137df9b312a5450099d021ca68ce7530',
            'redirect_uri':'https://www.google.com'
        },
        {
            'client_id':'9e64d1e9944f4117b703e5cf6bf162e2',
            'client_secret':'8848fa1a4dfd410abff5f8ffceb99ebd',
            'redirect_uri':'https://www.google.com'
        },
        {
            'client_id':'0e0261ccd9624bfa8ebaa1da6022c4bd',
            'client_secret':'1037c788f34148c8846a5a966fde68c4',
            'redirect_uri':'https://www.google.com'
        }
    ]
}

def print_in_box(text):
    border = '+' + '-' * (len(text) + 2) + '+'
    print(border)
    print(f"| {text} |")
    print(border)

def change_credentials():
    while True:
        try:
            random_account, random_account_credentials = random.choice(list(credentials_dicts.items()))
            random_credentials = random.choice(random_account_credentials)
            account_index = list(credentials_dicts.keys()).index(random_account)
            credentials_index = random_account_credentials.index(random_credentials)
            credentials_index_complete = account_index * len(random_account_credentials) + credentials_index
            custom_cache_handler = CustomCacheFileHandler(credentials_index=credentials_index_complete)
            print_in_box(f"ACCOUNT EMAIL: {random_account}")
            print_in_box(f"ACCOUNT CLIENT-ID: {random_credentials['client_id']}")
            with open("cache/credentials.txt", "w") as file:
                file.write(random_credentials['client_id'])
            spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(**random_credentials, scope="playlist-modify-private user-read-recently-played", cache_handler=custom_cache_handler))
            prova = spotify.current_user()['id']
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 429:
                with open("data/errors.txt", "a") as file:
                    retry_after = int(e.headers.get('Retry-After'))
                    file.write(random_credentials['client_id'] + retry_after + "\n")
            continue
        except spotipy.oauth2.SpotifyOauthError:
            continue
        else:
            break
    
    return spotify

def update_all_cache_files():
    with open("data/errors.txt", "a") as file:
        for email, apps in credentials_dicts.items():
            for app in apps:
                account_index = list(credentials_dicts.keys()).index(email)
                credentials_index = apps.index(app)
                credentials_index_complete = account_index * len(apps) + credentials_index
                custom_cache_handler = CustomCacheFileHandler(credentials_index=credentials_index_complete)
                print_in_box(f"ACCOUNT EMAIL: {email}")
                print_in_box(f"ACCOUNT CLIENT-ID: {app['client_id']}")
                try:
                    spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(**app, scope="playlist-modify-private user-read-recently-played", cache_handler=custom_cache_handler))
                    user_id = spotify.search("ligabue")
                    # Continua la gestione della risposta...
                except spotipy.SpotifyException as e:
                    if e.http_status == 429:
                        retry_after = int(e.headers.get('Retry-After'))
                        print(f"Too Many Requests. Retrying after {retry_after} seconds...")
                        continue
                    else:
                        print("Errore:", e)
                        file.write(app['client_id'])
                        file.write("\n")
                        file.write(str(e))
                        file.write("\n")
                        file.write("\n")
                        continue
                except Exception as e:
                    print(e)
                    file.write(app['client_id'])
                    file.write("\n")
                    file.write(str(e))
                    file.write("\n")
                    file.write("\n")
                    continue


def get_recommendations(spotify=change_credentials(), seed_tracks=None, limit=100, kwargs=None):  
    if kwargs:
        key = tuple(seed_tracks), tuple(kwargs.items())
    else:
        key = tuple(seed_tracks)

    with open("data/stored_recommendations.bin", "rb") as file:
        try:
            while True:
                recommendation = pickle.load(file)
                if recommendation.get(key, None):
                    print("Retrieved recommentations from local storage")
                    return recommendation[key]
        except (EOFError):
            pass
    
    ret = spotify.recommendations(seed_tracks=seed_tracks, limit=limit, kwargs=kwargs)
    with open("data/stored_recommendations.bin", "ab") as file:
        recommendations_dict = {key: ret}
        pickle.dump(recommendations_dict, file)
    print("Retrieved recommentations from Spotify API")

    return ret 