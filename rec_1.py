#Each song of the user’s listening history is used as input to the Spotify recommender
#system to get a similar song. Notice that since this playlist is generated song-by-song, no song-set is produced

from listening_history_manager import spotify, recently_played_songs

playlist_length = 24


def get_recommendations(features):
    playlist = []
    for song in features:
        modified_song_data = {'target_' + key: value for key, value in song.items() if key != 'id'}
        recommendations = spotify.recommendations(seed_tracks=[song['id']], limit=len(features), kwargs=modified_song_data).get('tracks')
        for track in recommendations:
            if track['id'] not in list(set(song['id'] for song in playlist)):
                playlist.append(track)
                break

    return playlist

def main():
    listening_history = list(set([track_item['track']['id'] for track_item in recently_played_songs]))[0:playlist_length]
    features = list(filter(None, spotify.audio_features(tracks=listening_history)))

    count = playlist_length
    while(len(listening_history) - len(features) > 0):
        feature = spotify.audio_features(tracks=[recently_played_songs[count]['track']['id']])[0]
        if feature:
            features.append(feature)
        count += 1

    playlist = get_recommendations(features)
    ids = [track['id'] for track in playlist]
        
    
if __name__ == "__main__":
    main()