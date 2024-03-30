# Spotify-Playlist-Generator
An automated method to generate highly personalized playlists

Installation Instructions:
1) Install the requirements listed in 'requirements.txt' (pip install -r requirements.txt)
2) Register your account to the Spotify Developer Dashboard at the link https://developer.spotify.com/dashboard.
  a) if you haven't already done so, you will need to verify the email associated to your Spotify account.
  b) after you have verified the email,  wait about five minutes: Spotify takes time to register your account to the Developer Dashboard.
3) Go to https://developer.spotify.com/dashboard and create an application 
4) For every application that you create, you have to insert the credentials 'client_id', 'client_secret' and 'redirect_uri' in the dictionary 'credentials_dicts' inside the module 'listening_history_manager.py'
5) Every time you try to run a module, a link will be prompted to you. Paste the link into a browser, login to Spotify, copy the URL you were redirected to, and paste it back into the program 
6) Run 'step1.py'
7) Run 'step2.py'

For experimental purposes you can also run 'other_methods.py' and 'evaluation.py'
