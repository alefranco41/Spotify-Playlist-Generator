from listening_history_manager import spotify
from step1 import feature_names_to_remove
from step2 import compute_optimal_solution, retrieve_data
import math


playlist_length = 24


#Each song of the user’s listening history is used as input to the Spotify recommender
#system to get a similar song. Notice that since this playlist is generated song-by-song, no song-set is produced
def get_rec_1_recommendations(listening_history):
    playlists = {}
    for period, songs in listening_history.items():
        playlist = []
        for song in songs:
            recommendation = spotify.recommendations(seed_tracks=[song['id']], limit=1).get('tracks')[0]
            if recommendation['id'] not in list(set(playlist)):
                playlist.append(recommendation['id'])
                if playlist_length == len(playlist):
                    playlists[period] = playlist
                    break

    return playlists

#To provide more contextual data to the recommender system, three songs of the
#user’s listening history (the current, the previous and the next) are used as input of the
#Spotify recommender system to get a similar song. Again, since the playlist is generated
#song-by-song, no song-set is produced
def get_rec_2_recommendations(listening_history):
    playlists = {}
    for period, songs in listening_history.items():
        playlist = []
        for i, song in enumerate(songs):
            if i == 0: 
                track_ids = [song, songs[i + 1]]
            elif i == len(songs) - 1: 
                track_ids = [songs[i - 1], song]
            else:
                track_ids = [songs[i - 1], song, songs[i + 1]]
        
            recommendation = spotify.recommendations(seed_tracks=[track['id'] for track in track_ids], limit=1).get('tracks')[0]
            if recommendation['id'] not in list(set(playlist)):
                playlist.append(recommendation['id'])
                if playlist_length == len(playlist):
                    playlists[period] = playlist
                    break

    return playlists


#A hybrid method that uses the Spotify recommendation system to generate a pool
#of candidate songs (i.e. the song-set), and uses our dynamic programming algorithm to select
#the songs to include in the user-tailored playlist, and to sort them. The song-set is created as
#follows. Since the maximum number of songs that can be passed to the recommender is five,
#we split the listening history in blocks composed of five consecutive songs. Then, for each
#block, the recommender is asked to return a number of songs so as to have a song-set of the
#same size as that of the dynamic programming method.
def get_hyb_1_recommendations(listening_history):
    playlists = {}

    for period, songs in listening_history.items():
        playlist = []
        blocks = [songs[i:i+5] for i in range(0, len(songs), 5) if len(songs[i:i+5]) == 5]

        limit = math.ceil(playlist_length / len(blocks))
        length = False

        for block in blocks:
            if length:
                playlists[period] = playlist
                break
            recommendations = spotify.recommendations(seed_tracks=[track['id'] for track in block], limit=playlist_length).get('tracks')
            for recommendation in recommendations:
                count = 0
                if recommendation['id'] not in list(set(playlist)):
                    playlist.append(recommendation['id'])
                    count += 1
                    if count == limit:
                        break
                    if playlist_length == len(playlist):
                        length = True
                        break
    
    playlist_patterns = {}

    for period, playlist in playlists.items():
        playlist_pattern_all_features = list(filter(None, spotify.audio_features(tracks=playlist)))
        playlist_pattern = [{key:value for key,value in song.items() if key not in feature_names_to_remove} for song in playlist_pattern_all_features]
        playlist_patterns[period] = playlist_pattern
    
    ordered_playlists = compute_optimal_solution(listening_history, playlist_patterns)
    return ordered_playlists

def main():
    current_period = 8 #int(datetime.now().hour)

    _, listening_history = retrieve_data() 

    listening_history_filtered = {period:songs for period, songs in listening_history.items() if period == current_period}

    playlist_rec_1 = get_rec_1_recommendations(listening_history_filtered)
    playlist_rec_2 = get_rec_2_recommendations(listening_history_filtered)
    playlist_hyb_1 = get_hyb_1_recommendations(listening_history_filtered)

if __name__ == "__main__":
    main()