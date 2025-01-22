import time
import sys
import os
import js2py
import threading
import urllib3
import queue
import requests 
from urllib3.exceptions import HTTPError
from urllib.error import URLError
from bs4 import BeautifulSoup
import json
import re
import logging
from datetime import datetime


class downloader:
    def __init__(self, nombre_threads=4):
         # File d'attente partagée entre les threads pour gérer les tâches de téléchargement
        self.download_queue = queue.Queue()
        
         # Liste pour stocker les objets Thread créés
        self.threads = []

         # Nombre de threads que le gestionnaire va lancer
        self.nombre_threads = nombre_threads

         # Initialisation et démarrage des threads pour traiter les tâches de la file
        self._initialize_threads()


    def _initialize_threads(self):
         # Boucle pour créer un nombre de threads égal à self.nombre_threads
        for _ in range(self.nombre_threads):
             # Crée un thread avec pour cible la méthode _gestionnaire_queue
             # Le paramètre daemon=True permet d'arrêter les threads automatiquement lorsque le programme principal se termine
            thread = threading.Thread(target=self._gestionnaire_queue, daemon=True)
            
             # Démarre le thread (il commence à exécuter _gestionnaire_queue en parallèle)
            thread.start()

             # Ajoute le thread à la liste des threads pour un suivi ou une gestion ultérieure
            self.threads.append(thread)
    
    def _gestionnaire_queue(self):
        while True: # Boucle infinie pour gérer en permanence les tâches dans la file d'attente
            try:
                 # Récupère une tâche dans la file avec un timeout de 1 seconde
                episode_info, episode_urls = self.download_queue.get(timeout=1)

                 # Déstructure les informations sur l'épisode et ses URL
                name, episode_number, episode_path, anime_json = episode_info
                
                 # Initialise un logger spécifique à cet épisode
                logger = logging.getLogger(f"anime: {name} {episode_number}")
                logger.info(f"download en cour")

                 # Vérifie si l'URL Sibnet est valide
                sibnet, vidmoly, sendvid = episode_urls
                if sibnet != "none":
                    status = self.sibnet_downloader(path=episode_path, url=sibnet)
                    if status == True: # Si le téléchargement a réussi
                        logger.info(f"sibnet download fini")
                        self._wirte_in_anime_json(number=episode_number, url=sibnet, anime_json=anime_json)
                        self.download_queue.task_done() # Marque la tâche comme terminée
                        continue
                
                 # Vérifie si l'URL Vidmoly est valide (non implémenté ici)
                if vidmoly != "none":
                    pass # Rien n'est fait ici
                
                 # Vérifie si l'URL Sendvid est valide
                if sendvid != "none": 
                    status = self.sendvid_downloader(path=episode_path, url=sendvid)
                    if status == True: # Si le téléchargement a réussi
                        logger.info(f"sendvid download fini")
                        self._wirte_in_anime_json(number=episode_number, url=sendvid, anime_json=anime_json)
                        self.download_queue.task_done()  # Marque la tâche comme terminée
                        continue
                
                 # Si aucune URL n'a fonctionné
                else:
                    logger.warning(f"no url work for")
                    self.download_queue.task_done()
                    
                    continue
                self.download_queue.task_done() # Marque la tâche comme terminée (redondant ici)
                continue

             # Si la file d'attente est vide, réessaie après 1 seconde
            except queue.Empty:
                continue

             # Gestion générique des exceptions
            except Exception as e:
                logger.error(f"Erreur dans le traitement de la queue: {e}")
                self.download_queue.task_done()
                continue

    
    def _add_to_queue(self, anime_info, new_episode, anime_json):
         # Initialise un logger pour suivre les opérations sur cet anime et sa saison
        logger = logging.getLogger(f"anime: {anime_info[1]} season {anime_info[2]}")
         # Détermine le chemin où les épisodes seront stockés en fonction de la langue
        if anime_info[3] == "vostfr":
            anime_path = rf"C:\Users\dahoe\Documents\code\anime-sama\vo/{anime_info[1]}/season {anime_info[2]}/"
        elif anime_info[3] == "vf":
            anime_path = rf"C:\Users\dahoe\Documents\code\anime-sama\vf/{anime_info[1]}/season {anime_info[2]}/"
        elif anime_info[3] == "vf1":
            anime_path = rf"C:\Users\dahoe\Documents\code\anime-sama\vf/{anime_info[1]}/season {anime_info[2]}/"
        elif anime_info[3] == "vf2":
            anime_path = rf"C:\Users\dahoe\Documents\code\anime-sama\vf/{anime_info[1]}/season {anime_info[2]}/"
        else:
            # Avertit si la langue n'est pas prise en charge
            logger.warning(f"langage not supported: {anime_info[3]}")
        
         # Crée le répertoire cible si nécessaire
        if not os.path.exists(anime_path):
            os.makedirs(anime_path)

         # Ajoute chaque épisode dans la file de téléchargement
        for number, episode_urls in new_episode:
             # Détermine le chemin complet du fichier de l'épisode
            episode_path = f"{anime_path}{anime_info[1]} s{anime_info[2]} {int(number):02d}.mp4"
            
             # Crée une structure avec les informations de l'épisode
            episode_info = ((f"{anime_info[1]} season {anime_info[2]}", f"{int(number):02d}", episode_path, anime_json))
            
             # Ajoute l'épisode et ses URLs dans la file de téléchargement
            self.download_queue.put((episode_info, episode_urls))
    
    def _wirte_in_anime_json(self, number, url, anime_json):
         # Initialise un logger pour suivre l'opération sur ce fichier JSON
        logger = logging.getLogger(f"{anime_json} | {number}:{url} ")

        try:
             # Ouvre le fichier JSON en mode lecture/écriture avec encodage UTF-8
            with open(anime_json, 'r+', encoding='utf-8') as file:
                data = json.load(file)

             # Met à jour le dictionnaire avec le nouvel épisode et son URL
            data[number] = url
            
             # Réécrit le fichier JSON avec les nouvelles données, formatées proprement
            with open(anime_json, 'w') as file:
                json.dump(data, file, indent=4)

             # Gestion des exceptions possibles
        except PermissionError as e:
             # Si l'accès au fichier est refusé
            logger.warning(f"Erreur de permission : {e}")
        except FileNotFoundError as e:
             # Si le fichier JSON n'existe pas
            logger.error(f"Fichier non trouvé : {e}")
        except json.JSONDecodeError as e:
             # Si le contenu du fichier JSON est corrompu ou mal formé
            logger.error(f"Erreur de décodage JSON : {e}")
        except Exception as e:
             # Pour toute autre erreur inattendue
            logger.error(f"Erreur inattendue : {e}")

    def sibnet_downloader(self, path, url):
        def _init_(path, url):
             # Définit les en-têtes HTTP pour simuler une requête légitime venant d'un navigateur
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36", "Referer": f"https://video.sibnet.ru"}
            
             # Tente d'extraire l'URL directe du fichier MP4 depuis la page HTML
            mp4_url = extract_mp4_url(url=url)

             # Si l'URL MP4 n'a pas été trouvée, retourne un échec
            if mp4_url == False:
                status = False
            else:
                 # Sinon, démarre le téléchargement avec les en-têtes et l'URL extraits
                status = downloading(headers=headers, url=mp4_url, path=path)
            return status

        def extract_mp4_url(url):
            logger = logging.getLogger(f"sibnet_downloader")
            try:
                 # Effectue une requête GET vers l'URL de la vidéo
                response = requests.get(url)
                response.raise_for_status()

                 # Parse le contenu HTML pour chercher les scripts
                soup = BeautifulSoup(response.content, 'html.parser')
                scripts = soup.find_all('script', type="text/javascript")

                 # Parcourt chaque script pour trouver l'URL de la vidéo MP4
                for script in scripts:
                    script_content = script.string
                    if script_content:
                         # Recherche de l'URL de la vidéo dans les scripts
                        match = re.search(r'player\.src\(\[\{src: "(.*?)"', script_content)
                        if match:
                            video_url = match.group(1) # Capture l'URL dans le script
                            url = f"https://video.sibnet.ru{video_url}"
                            return url
            except HTTPError as e:
                 # Logue une erreur HTTP si la requête échoue
                logger.error(f"HTTP Error occurred during download: {e}")
                return False
            except URLError as e:
                 # Logue une erreur d'URL si elle est invalide
                logger.error(f"URL Error occurred during download: {e}")
                return False
            except Exception as e:
                 # Capture toute autre exception imprévue
                logger.error(f"Exception Error occurred during download: {e}")
                return False
        
        def downloading(headers, url, path):
             # Logger pour suivre les opérations spécifiques à Sibnet
            logger = logging.getLogger(f"sibnet_downloader")
             # Réduit la verbosité des logs pour les requêtes HTTP
            urllib3_logger = logging.getLogger("urllib3")
            urllib3_logger.setLevel(logging.WARNING)

            try:
                 # Initialise un gestionnaire de connexions HTTP (pool de connexions)
                http = urllib3.PoolManager()
                 # Effectue une requête GET vers l'URL avec les en-têtes spécifiés
                response = http.request('GET', url, headers=headers, preload_content=False)

                 # Vérifie si la réponse HTTP indique un succès (code 200)
                if response.status == 200:
                    #total_size = int(response.headers.get('content-length', 0))
                     # Définition de la taille des blocs à télécharger (1 MB par bloc)
                    block_size = 1048576

                     # Ouvre un fichier en mode écriture binaire pour enregistrer les données
                    with open(path, "wb") as f:
                         # Parcourt les données téléchargées par blocs et les écrit dans le fichier
                        for block_num, data in enumerate(response.stream(block_size), 1):
                            f.write(data)

                     # Indique que le téléchargement a réussi
                    return True
                else:
                     # Logue une erreur si le statut HTTP n'est pas 200
                    logger.error(f"Url response: {response.status}")
                    return False

             # Gestion des erreurs d'URL (malformée ou inaccessible)
            except HTTPError as e:
                logger.error(f"HTTP Error occurred during download: {e}")
                return False

             # Gestion des erreurs d'URL (malformée ou inaccessible)
            except URLError as e:
                logger.error(f"URL Error occurred during download: {e}")
                return False

             # Gestion des erreurs générales imprévues
            except Exception as e:
                logger.error(f"Exception Error occurred during download: {e}")
                return False

        status = _init_(path=path, url=url)
        return status

    def vidmoly_downloader(self, path, url):
     # Cette méthode est définie pour gérer le téléchargement depuis Vidmoly, mais elle est actuellement vide.
        pass

    def sendvid_downloader(self, path, url):
    # Cette méthode gère le téléchargement des vidéos depuis Sendvid.
        def _init_(path, url):
        # Initialisation : extrait l'URL du fichier MP4 et démarre le téléchargement.
            mp4_url = extract_mp4_url(url=url) # Appelle la fonction pour obtenir l'URL du fichier vidéo MP4.
            status = downloading(path=path, url=mp4_url) # Télécharge la vidéo à l'emplacement spécifié.
            return status # Retourne le statut du téléchargement.

        def extract_mp4_url(url):
            # Extrait l'URL directe du fichier MP4 depuis la page HTML.
            response = requests.get(url) # Envoie une requête GET à l'URL.
            response.raise_for_status() # Vérifie que la requête a réussi, sinon lève une exception.
            soup = BeautifulSoup(response.content, 'html.parser') # Analyse le contenu HTML.
            # Recherche un tag <meta> avec la propriété "og:video", qui contient l'URL de la vidéo.
            meta_tag = soup.find("meta", property="og:video")
            # Si trouvé, retourne l'attribut "content" contenant l'URL, sinon retourne None.
            mp4_url = meta_tag['content'] if meta_tag else None
            return mp4_url
        
        def downloading(url, path):
        # Télécharge le fichier depuis une URL vers un chemin local.
            logger = logging.getLogger(f"sendvid_downloader") # Initialise un logger pour cette fonction.
            urllib3_logger = logging.getLogger("urllib3") # Configure le logger d'urllib3.
            urllib3_logger.setLevel(logging.WARNING) # Réduit les logs d'urllib3 au niveau WARNING.
            try:
                http = urllib3.PoolManager()  # Initialise un gestionnaire de connexion HTTP.
                response = http.request('GET', url, preload_content=False) # Envoie une requête GET sans charger tout le contenu en mémoire.
                if response.status == 200: # Vérifie que la réponse HTTP est OK.
                    #total_size = int(response.headers.get('content-length', 0))
                    block_size = 1048576 # Définit la taille des blocs à télécharger (1 MB par bloc).
                    with open(path, "wb") as f: # Ouvre le fichier de destination en mode écriture binaire.
                        for block_num, data in enumerate(response.stream(block_size), 1): # Télécharge les données par blocs.
                            f.write(data) # Écrit chaque bloc dans le fichier.
                    return True # Indique que le téléchargement a réussi.
                else:
                    logger.error(f"Url response: {response.status}") # Log une erreur si le statut HTTP n'est pas OK.
                    return False
            except HTTPError as e:
                logger.error(f"HTTP Error occurred during download: {e}") # Log une erreur HTTP.
                return False
            except URLError as e:
                logger.error(f"URL Error occurred during download: {e}")  # Log une erreur d'URL.
                return False
            except Exception as e:
                logger.error(f"Exception Error occurred during download: {e}")  # Log toute autre exception.
                return False

        # Démarre le processus d'initialisation pour télécharger la vidéo.
        status = _init_(path=path, url=url)
        return status  # Retourne le statut final du téléchargement.

 
class main:
    def __init__(self, times):
        # Initialisation de la classe principale.
        script_dir = os.path.dirname(sys.argv[0]) # Obtient le répertoire du script.

        # Configure le logger principal pour enregistrer les logs dans un fichier et sur la console.
        log_filename = datetime.now().strftime('app_%Y-%m-%d_%H-%M-%S.log')
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s - %(name)s %(message)s',
            handlers=[
                logging.StreamHandler(),  # Affiche les logs dans la console. 
                logging.FileHandler(f"{script_dir}/data/logs/{log_filename}")]) # Enregistre les logs dans un fichier.
        logger = logging.getLogger("init") # Initialise un logger pour l'initialisation.

        # Définit les chemins et URL nécessaires au script.
        anime_json = f'{script_dir}/data/anime.json' # Fichier contenant la liste des animes.
        as_base_url = "https://anime-sama.fr/catalogue/" # URL de base pour les animes.
        episode_js = f'{script_dir}/data/download/episode.js' # Fichier temporaire pour les épisodes.

        # Initialise un gestionnaire de téléchargement avec 4 threads.
        self.downloader = downloader(nombre_threads=4)

         # Boucle principale : exécute le traitement et attend entre chaque itération.
        while True:
            self.start(script_dir, anime_json, as_base_url, episode_js)
            self.countdown_timer(times)

    def countdown_timer(self, seconds):
        # Affiche un compte à rebours en secondes avant de redémarrer le traitement.
        logger = logging.getLogger("timer")
        while seconds:
            hours, remainder = divmod(seconds, 3600) # Convertit les secondes en heures, minutes et secondes.
            mins, secs = divmod(remainder, 60)
            timer = f'{hours:02d}:{mins:02d}:{secs:02d}' # Formate le temps en hh:mm:ss.
            print(timer, end="\r")  # Affiche le compte à rebours sur la même ligne.
            time.sleep(1)  # Attend une seconde.
            seconds -= 1
        logger.info("starting traitement")  # Log que le traitement va démarrer.

    def start(self, script_dir, anime_json, as_base_url, episode_js):
        # Démarre le traitement pour chaque anime.
        logger = logging.getLogger(f"Anime Traitement")
        anime_infos = self.build_url(as_base_url=as_base_url, anime_json=anime_json) # Récupère les informations des animes.
        queue = []  # Initialise une file d'attente pour les tâches de téléchargement.
        if anime_infos:
            for anime_info in anime_infos:  # Parcourt chaque anime pour vérifier les nouveaux épisodes.
                logger = logging.getLogger(f"anime: {anime_info[1]} saison {anime_info[2]}")
                logger.info(f"scan en cour")
                logger.info(f"url: {anime_info[0]}")

                # Définit les chemins des fichiers pour les données de téléchargement et d'anime.
                download_path = f"{script_dir}/data/download/{anime_info[1]} s{anime_info[2]}.json"
                anime_path = f"{script_dir}/data/anime/{anime_info[1]} s{anime_info[2]}.json"

                # Vérifie si "episodes.js" est disponible pour cet anime.
                is_download = self.find_episodejs(anime_info=anime_info, episode_js=episode_js)
                if is_download == True: 
                    # Extrait les liens des épisodes et compare les nouveaux épisodes.
                    self.extract_link(download_path=download_path, episode_js=episode_js)
                    new_episode = self.compare_json(download_path=download_path, anime_path=anime_path)
                    if new_episode:
                        queue.append((anime_info, new_episode, anime_path))  # Ajoute à la file d'attente.

                    for numb, link in new_episode:
                        logger.info(f"!!!! nouveaux !!!! episode {numb}, {link}") # Log les nouveaux épisodes.
                logger.info(f"scan en terminer") # Log que le scan est terminé.

            # Ajoute les nouveaux épisodes détectés dans la file d'attente du gestionnaire de téléchargement.
            for anime_info, new_episode, anime_path in queue:    
                self.downloader._add_to_queue(anime_info, new_episode, anime_path)
        else:
            logger.warning(f"anime.json is empty") # Log un avertissement si la liste des animes est vide.

    
    def build_url(self, as_base_url, anime_json):
        # Construit les URLs pour chaque anime à partir des données JSON.
         with open(anime_json, 'r') as file:
            data = json.load(file) # Charge les données du fichier JSON.

            anime_info = [] # Initialise la liste des informations d'animes.
            for entry in data: # Parcourt chaque entrée du fichier JSON.
                comment = entry.get("__comment") # Ignore les entrées marquées comme commentaire.
                if comment: 
                    continue

                # Récupère les informations nécessaires : nom, saison, langue.
                name = entry.get('name')
                if name == "none":  # Ignore les entrées sans nom valide.
                    continue
                season = entry.get('season')
                langage = entry.get('langage')
                # Construit l'URL complète pour cet anime.
                url = f"{as_base_url}{name}/saison{season}/{langage}/"
                anime_info.append((url, name, season, langage)) # Ajoute les informations à la liste.

            return anime_info # Retourne la liste des informations d'animes.
        
    def find_episodejs(self, anime_info, episode_js):
    # Récupère le fichier "episodes.js" pour un anime donné et le sauvegarde dans un fichier local.
        logger = logging.getLogger(f"anime: {anime_info[1]} saison {anime_info[2]}") # Initialise un logger pour cet anime.
        # Envoie une requête GET à l'URL principale de l'anime pour récupérer le contenu de la page.
        response = requests.get(anime_info[0])
        if response.status_code == 200: # Vérifie si la requête a réussi (statut 200).
            soup = BeautifulSoup(response.content, 'html.parser') # Parse le HTML de la réponse pour l'analyser.
            # Recherche un tag <script> dont l'attribut "src" contient "episodes.js".
            script_tag = soup.find('script', src=lambda x: x and 'episodes.js?' in x)
            if script_tag: # Si un tel tag est trouvé.
                script_url = script_tag['src']# Extrait l'URL du fichier "episodes.js".
                # Si l'URL est relative, la convertir en URL absolue.
                if not script_url.startswith('http'):
                    script_url = anime_info[0].rstrip('/') + '/' + script_url.lstrip('/')
                    # Si l'URL est relative, la convertir en URL absolue.
                    script_response = requests.get(url=script_url, stream=True)
                    
                    if script_response.status_code == 200: # Vérifie si le téléchargement du fichier a réussi.
                        with open(episode_js, 'wb') as file:
                            file.write(script_response.content)    # Sauvegarde le fichier localement.
                        return True # Retourne True si le téléchargement est réussi.
            else:
                # Si aucun tag <script> correspondant n'est trouvé, log un avertissement.
                logger.warning(f"episode.js was not found: {script_url}")
                return False
        else:
            # Log un avertissement si la page principale n'est pas accessible.
            logger.warning(f"url not work: {anime_info[0]}")
            return False
         
    def extract_link(self, download_path, episode_js):
        # Extrait les liens d'épisodes à partir du fichier "episodes.js" et les regroupe par domaine.
        logger = logging.getLogger(f"Extract Link") # Initialise un logger pour cette fonction.
        
        # Lit le contenu du fichier "episodes.js".       
        with open(episode_js, 'r') as file:
            js_content = file.read()
        
        # Crée un interpréteur JavaScript pour exécuter le contenu du fichier.
        context = js2py.EvalJs()
        context.execute(js_content) # Exécute le code JavaScript contenu dans le fichier.

        # Définit les variables d'épisodes à vérifier et les domaines pris en charge.
        variables_to_check = ['eps1', 'eps2', 'eps3', 'eps4', 'eps5', 'eps6', 'eps7', 'eps8']
        domains = {"video.sibnet.ru": [], "vidmoly.to": [], "sendvid.com": []}

        def count_domain_urls(python_array, domains):
            # Compte le nombre de liens pour chaque domaine.
            counts = {domain: 0 for domain in domains.keys()} # Initialise un compteur pour chaque domaine.
            for item in python_array: # Parcourt chaque lien de l'array Python.
                if 'vk.com' in item: # Ignore les liens de "vk.com"
                    continue 
                for domain in counts.keys(): # Vérifie si le lien appartient à un domaine connu.
                    if domain in item:
                        counts[domain] += 1
            return counts

        def is_matching_domain(url, domain):
            # Vérifie si une URL appartient exactement à un domaine donné.
            if '://' in url:
                url = url.split('://', 1)[1] # Retire le protocole (http/https).
            extracted_domain = url.split('/', 1)[0] # Extrait le domaine principal de l'URL.
            return extracted_domain == domain
        
        def number_urls(domain, url_list):
            # Filtre et numérote les URLs uniques pour un domaine donné.
            numbered_list = [] # Contient les URLs numérotées.
            seen_urls = set() # Utilisé pour éviter les doublons.
            for i, url in enumerate(url_list): # Parcourt chaque URL.
                if url and url not in seen_urls and is_matching_domain(url, domain):
                    numbered_list.append(url) # Ajoute l'URL si elle est unique et correspond au domaine.
                    seen_urls.add(url) # Ajoute l'URL au set des URLs vues.
                else:
                    numbered_list.append(None) # Ajoute None pour les doublons ou URLs invalides.
            return numbered_list
        

        for var_name in variables_to_check: # Parcourt chaque variable d'épisodes.
            try:
                # Récupère la variable JavaScript depuis le contexte.
                js_object = getattr(context, var_name)
                # Convertit la variable en tableau Python si nécessaire.
                if isinstance(js_object, js2py.base.JsObjectWrapper):
                    js_array = list(js_object)
                else:
                    js_array = js_object
                
                if isinstance(js_array, str):
                    python_array = [js_array]
                else:
                    python_array = list(js_array) # Convertit en liste Python.
                
                counts = count_domain_urls(python_array, domains) # Compte les URLs par domaine.
                max_domain = max(counts, key=counts.get) # Trouve le domaine avec le plus de liens.
                if counts[max_domain] > 0: # Si des liens sont trouvés pour ce domaine.
                    domains[max_domain].extend(python_array) # Ajoute les liens à la liste du domaine.
            except js2py.internals.simplex.JsException as e: # Ignore les erreurs de parsing JavaScript.
                pass
        
        max_length = max(len(urls) for urls in domains.values()) # Trouve la longueur maximale parmi les listes de domaines.
        for domain in domains: # Équilibre les longueurs des listes pour chaque domaine.
            while len(domains[domain]) < max_length:
                domains[domain].append(None) # Ajoute None aux listes plus courtes.

        # Numérote les liens pour chaque domaine.
        numbered_domains = {domain: number_urls(domain, domains[domain]) for domain in domains.keys()}
        # Construit un dictionnaire JSON pour organiser les liens par numéro d'épisode.
        json_output = {}
        for i in range(max_length):
            json_output[str(i + 1)] = [numbered_domains["video.sibnet.ru"][i] if i < len(numbered_domains["video.sibnet.ru"]) else None,numbered_domains["vidmoly.to"][i] if i < len(numbered_domains["vidmoly.to"]) else None,numbered_domains["sendvid.com"][i] if i < len(numbered_domains["sendvid.com"]) else None]
        
        # Remplace les valeurs None par "none" dans le dictionnaire JSON.
        for key in json_output:
            json_output[key] = [url if url is not None else "none" for url in json_output[key]]
        # Sauvegarde le résultat dans un fichier JSON.
        with open(download_path, 'w') as json_file:
            json.dump(json_output, json_file, indent=4)

    def compare_json(self, download_path, anime_path):
        # Compare deux fichiers JSON pour trouver les nouveaux épisodes.
        with open(download_path, 'r', encoding='utf-8') as file1:
            data1 = json.load(file1) # Charge les données JSON du fichier téléchargé.
        
        # Si le fichier cible n'existe pas, le créer avec une structure vide.
        if not os.path.exists(anime_path):
            json_structure = {}
            with open(anime_path, 'w') as json_file:
                json.dump(json_structure, json_file, indent=4)

        with open(anime_path, 'r', encoding='utf-8') as file2:
            data2 = json.load(file2) # Charge les données JSON du fichier existant.
            
        new_entries = [] # Stocke les nouveaux épisodes détectés.
        
        keys2 = {int(k) for k in data2.keys() if k.isdigit()}  # Récupère les clés numériques du fichier existant.
        
        for key in data1: # Parcourt chaque clé du fichier téléchargé.
            num_key = int(key)
            if num_key not in keys2:  # Vérifie si la clé n'est pas dans le fichier existant.
                new_entries.append((key, data1[key])) # Ajoute la clé et les données associées.
        return new_entries  # Retourne les nouveaux épisodes trouvés.

if __name__ == "__main__":
    main(times=3600) # Initialise la boucle principale avec un délai de 3600 secondes (1 heure).