# Spotify-Playlist-Generator
An automated method to generate highly personalized playlists

Prerequisite: Spotify's extended listening history
1) Log in to your Spotify account through a browser.
2) Go to the "Account" section using the drop-down menu at the top right.
3) Click on "Privacy Settings."
4) Select "Extended Listening History" from the "Download your data" section.
5) Press the "Request data" button.
6) Complete the reCAPTCHA if prompted to prove you're not a robot.
7) Click on the "Confirm" button in the email received from Spotify.
8) After several days, you will receive an email notifying you that the requested data is ready for download. Click on the "Download" button in this email within 14 days.
9) Confirm your identity by entering your account password. The file "my_spotify_data.zip" will be downloaded automatically.
Retrieve the file "Streaming_History_Audio_XXXX-YYYY_Z.json" from "my_spotify_data.zip," where "XXXX-YYYY" indicates the reference period of the history (e.g., 2023-2024) and "Z" is a progressive number used to split the history into multiple files if it contains many songs. In our case, you are asked to share the first history file (with "Z" equal to "0") for the last available year. This file contains the most important data, such as IDs, audio features, and listening times for each song listened to during the reference period.
10) When running the application, insert the listening history file path when asked.


Installation Instructions:
1) Install the requirements listed in 'requirements.txt' (pip install -r requirements.txt)
2) Register one or more Spotify accounts to the Spotify Developer Dashboard at the link https://developer.spotify.com/dashboard.
  a) if you haven't already done so, you will need to verify the email associated to your Spotify accounts.
  b) after you have verified the email,  wait about five minutes: Spotify takes time to register your accounts to the Developer Dashboard.
3) Go to https://developer.spotify.com/dashboard and create up to five application for each Spotify account.
4) For every application that you create, you have to insert the credentials 'client_id', 'client_secret' and 'redirect_uri' in the dictionary 'credentials_dicts' inside the module 'listening_history_manager'. Each key of 'credentials_dicts' is the email associated to a Spotify account, and each value is a list of (up to five) application credentials associated to that account. The more applications you create, the lower will be the chances of reaching the API request limit imposed by Spofify. Indeed, every time the software is used, the credentials of a random application are chosen. 
7) Run the module 'playlist_generator'. Whenever you are prompted a redirect URL, you have to:
  a) paste the URL into a browser
  b) login to the corresponding Spotify account (the email will be printed to stdout before the URL)
  c) after the login, paste the link to the page you have been redirected to back to stdin.
8) if every step was done correctly, you should be able to see the generated playlist on your Spotify account.

Options:
-d day: generate playlist for the specified day. The day must be one of the following: "Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"
-h hour: generate playlist for the specified hour. The hour must be an integer between 0 and 23
-f extended_listening_history: specify the path to the listening history file given by Spotify
