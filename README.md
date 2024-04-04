# Spotify-Playlist-Generator
An automated method to generate highly personalized playlists

Installation Instructions:
1) Install the requirements listed in 'requirements.txt' (pip install -r requirements.txt)
2) Register one or more Spotify accounts to the Spotify Developer Dashboard at the link https://developer.spotify.com/dashboard.
  a) if you haven't already done so, you will need to verify the email associated to your Spotify accounts.
  b) after you have verified the email,  wait about five minutes: Spotify takes time to register your accounts to the Developer Dashboard.
3) Go to https://developer.spotify.com/dashboard and create up to five application for each Spotify account.
4) For every application that you create, you have to insert the credentials 'client_id', 'client_secret' and 'redirect_uri' in the dictionary 'credentials_dicts' inside the module 'listening_history_manager'. Each key of 'credentials_dicts' is the email associated to a Spotify account, and each value is a list of (up to five) application credentials associated to that account. The more applications you create, the lower will be the chances of reaching the API request limit imposed by Spofify. Indeed, every time the software is used, the credentials of a random application are chosen. 
5) (optional) you can change the variables 'current_day' and 'current_hour' inside the module 'playlist_generator' in order to generate a playlist for a different time of the day.
6) (optional) you can comment the line 79 of the module 'playlist_generator' to generate (and upload on Spotify) only the playlist generated with our method.
7) Run the module 'playlist_generator'. Whenever you are prompted a redirect URL, you have to:
  a) paste the URL into a browser
  b) login to the corresponding Spotify account (the email will be printed to stdout before the URL)
  c) after the login, paste the link to the page you have been redirected to back to stdin.
