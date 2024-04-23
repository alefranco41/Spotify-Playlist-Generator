# update_credentials.py

import re

# Leggi solo l'ultima riga dal file cache/credentials.txt
with open('cache/credentials.txt', 'r') as credentials_file:
    lines = credentials_file.readlines()
    if lines:
        client_id_to_remove = lines[-1].strip()
    else:
        print("Il file cache/credentials.txt è vuoto.")
        exit()

# Leggi il contenuto del file listening_history_manager.py
with open('listening_history_manager.py', 'r') as file:
    file_content = file.read()

# Sostituisci solo l'ultimo client_id con una stringa vuota
file_content = re.sub(
    r"'client_id':'{}'".format(re.escape(client_id_to_remove)),
    "'client_id':''",
    file_content,
    count=1,
)

# Scrivi il file con le modifiche
with open('listening_history_manager.py', 'w') as file:
    file.write(file_content)
