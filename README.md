# Spotify-Playlist-Generator
An automated method to generate highly personalized playlists

Installation Instructions:
1) Install the requirements listed in 'requirements.txt' (pip install -r requirements.txt)
2) Register your account to the Spotify Developer Dashboard.
3) Go to https://developer.spotify.com/dashboard and create an application 
4) Use the credentials of the application to set up the variables 'client_id', 'client_secret' and 'redirect_uri' in the file 'listening_history_manager.py'
5) Run 'step1.py'
6) If it's the first run, a link will be prompted to you. Paste the link into a browser, login to Spotify, copy the URL you were redirected to, and paste it back into the program 
7) Run 'step2.py'
8) If you reach the Spotify API requests limit, the application will not work. In this case, you can either:
  a) wait for about one day
  b) delete the '.cache' file and go back to step 3)
