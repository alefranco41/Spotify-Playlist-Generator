import pickle
from spotipy.oauth2 import SpotifyOAuth
import spotipy
from datetime import datetime
import math
import random
import os
from custom_cache_handler import CustomCacheFileHandler

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
            'client_id':'',
            'client_secret':'',
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
            'client_id':'21af97baf6be400a98b4ff51ba49dd5d',
            'client_secret':'52ce1b28572945fdae471bfdcfc7310d',
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
            'client_id':'',
            'client_secret':'',
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
            'client_id':'',
            'client_secret':'',
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
            'client_id':'',
            'client_secret':'',
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
            'client_id':'',
            'client_secret':'',
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
            'client_id':'',
            'client_secret':'',
            'redirect_uri':''
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
            'client_id':'',
            'client_secret':'',
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
            'client_id':'9726d6e0aae544248849b2b9a587a546',
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
            'client_id':'3749253b8f004738a49ba7cbf6556221',
            'client_secret':'d43f9613e7594a27bbfa4be4664fb0a4',
            'redirect_uri':'https://www.google.com'
        },

        {
            'client_id':'560a43d92ef240bfb6a8bebcb485db45',
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
            'client_id':'0bf970ed08ab4cc19b453b1d03a97f1e',
            'client_secret':'f61e0868c28340ec965fb84bce0ed7f9',
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
    ]
}


def change_credentials():
    while True:
        try:
            random_account, random_account_credentials = random.choice(list(credentials_dicts.items()))
            random_credentials = random.choice(random_account_credentials)
            account_index = list(credentials_dicts.keys()).index(random_account)
            credentials_index = random_account_credentials.index(random_credentials)
            credentials_index_complete = account_index * len(random_account_credentials) + credentials_index
            custom_cache_handler = CustomCacheFileHandler(credentials_index=credentials_index_complete)
            spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(**random_credentials, scope="playlist-modify-private user-read-recently-played", cache_handler=custom_cache_handler))
        except spotipy.oauth2.SpotifyOauthError:
            continue
        else:
            break
    print(f"ACCOUNT EMAIL: {random_account}")
    print(f"ACCOUNT CLIENT-ID: {random_credentials['client_id']}")
    
    return spotify

