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
        self.download_queue = queue.Queue()
        self.threads = []
        self.nombre_threads = nombre_threads
        self._initialize_threads()


    def _initialize_threads(self):
        for _ in range(self.nombre_threads):
            thread = threading.Thread(target=self._gestionnaire_queue, daemon=True)
            thread.start()
            self.threads.append(thread)
    
    def _gestionnaire_queue(self):
        while True:
            try:
                episode_info, episode_urls = self.download_queue.get(timeout=1)
                name, episode_number, episode_path, anime_json = episode_info
                logger = logging.getLogger(f"anime: {name} {episode_number}")
                logger.info(f"download en cour")

                sibnet, vidmoly, sendvid = episode_urls
                if sibnet != "none":
                    status = self.sibnet_downloader(path=episode_path, url=sibnet)
                    if status == True:
                        logger.info(f"sibnet download fini")
                        self._wirte_in_anime_json(number=episode_number, url=sibnet, anime_json=anime_json)
                        self.download_queue.task_done()
                        continue
                if vidmoly != "none":
                    pass
                if sendvid != "none": 
                    status = self.sendvid_downloader(path=episode_path, url=sendvid)
                    if status == True:
                        logger.info(f"sendvid download fini")
                        self._wirte_in_anime_json(number=episode_number, url=sendvid, anime_json=anime_json)
                        self.download_queue.task_done()
                        continue
                else:
                    logger.warning(f"no url work for")
                    self.download_queue.task_done()
                    continue
                self.download_queue.task_done()
                continue
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Erreur dans le traitement de la queue: {e}")
                self.download_queue.task_done()
                continue

    
    def _add_to_queue(self, anime_info, new_episode, anime_json):
        logger = logging.getLogger(f"anime: {anime_info[1]} season {anime_info[2]}")
        if anime_info[3] == "vostfr":
            anime_path = rf"C:\Users\dahoe\Documents\code\anime-sama\vo/{anime_info[1]}/season {anime_info[2]}/"
        elif anime_info[3] == "vf":
            anime_path = rf"C:\Users\dahoe\Documents\code\anime-sama\vf/{anime_info[1]}/season {anime_info[2]}/"
        elif anime_info[3] == "vf1":
            anime_path = rf"C:\Users\dahoe\Documents\code\anime-sama\vf/{anime_info[1]}/season {anime_info[2]}/"
        elif anime_info[3] == "vf2":
            anime_path = rf"C:\Users\dahoe\Documents\code\anime-sama\vf/{anime_info[1]}/season {anime_info[2]}/"
        else:
            logger.warning(f"langage not supported: {anime_info[3]}")
        
        if not os.path.exists(anime_path):
            os.makedirs(anime_path)

        for number, episode_urls in new_episode:
            episode_path = f"{anime_path}{anime_info[1]} s{anime_info[2]} {int(number):02d}.mp4"

            episode_info = ((f"{anime_info[1]} season {anime_info[2]}", f"{int(number):02d}", episode_path, anime_json))
            
            self.download_queue.put((episode_info, episode_urls))
    
    def _wirte_in_anime_json(self, number, url, anime_json):
        logger = logging.getLogger(f"{anime_json} | {number}:{url} ")
        try:
            with open(anime_json, 'r+', encoding='utf-8') as file:
                data = json.load(file)

            data[number] = url
            
            with open(anime_json, 'w') as file:
                json.dump(data, file, indent=4)
        except PermissionError as e:
            logger.warning(f"Erreur de permission : {e}")
        except FileNotFoundError as e:
            logger.error(f"Fichier non trouvé : {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de décodage JSON : {e}")
        except Exception as e:
            logger.error(f"Erreur inattendue : {e}")

    def sibnet_downloader(self, path, url):
        def _init_(path, url):
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.190 Safari/537.36", "Referer": f"https://video.sibnet.ru"}
            mp4_url = extract_mp4_url(url=url)

            if mp4_url == False:
                status = False
            else:
                status = downloading(headers=headers, url=mp4_url, path=path)
            return status

        def extract_mp4_url(url):
            logger = logging.getLogger(f"sibnet_downloader")
            try:
                response = requests.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                scripts = soup.find_all('script', type="text/javascript")
                for script in scripts:
                    script_content = script.string
                    if script_content:
                        match = re.search(r'player\.src\(\[\{src: "(.*?)"', script_content)
                        if match:
                            video_url = match.group(1)
                            url = f"https://video.sibnet.ru{video_url}"
                            return url
            except HTTPError as e:
                logger.error(f"HTTP Error occurred during download: {e}")
                return False
            except URLError as e:
                logger.error(f"URL Error occurred during download: {e}")
                return False
            except Exception as e:
                logger.error(f"Exception Error occurred during download: {e}")
                return False
        
        def downloading(headers, url, path):
            logger = logging.getLogger(f"sibnet_downloader")
            urllib3_logger = logging.getLogger("urllib3")
            urllib3_logger.setLevel(logging.WARNING)
            try:
                http = urllib3.PoolManager()
                response = http.request('GET', url, headers=headers, preload_content=False)
                if response.status == 200:
                    #total_size = int(response.headers.get('content-length', 0))
                    block_size = 1048576
                    with open(path, "wb") as f:
                        for block_num, data in enumerate(response.stream(block_size), 1):
                            f.write(data)
                    return True
                else:
                    logger.error(f"Url response: {response.status}")
                    return False
            except HTTPError as e:
                logger.error(f"HTTP Error occurred during download: {e}")
                return False
            except URLError as e:
                logger.error(f"URL Error occurred during download: {e}")
                return False
            except Exception as e:
                logger.error(f"Exception Error occurred during download: {e}")
                return False

        status = _init_(path=path, url=url)
        return status

    def vidmoly_downloader(self, path, url):
        pass

    def sendvid_downloader(self, path, url):
        def _init_(path, url):
            mp4_url = extract_mp4_url(url=url)

            status = downloading(path=path, url=mp4_url)
            return status

        def extract_mp4_url(url):
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            meta_tag = soup.find("meta", property="og:video")
            mp4_url = meta_tag['content'] if meta_tag else None
            return mp4_url
        
        def downloading(url, path):
            logger = logging.getLogger(f"sendvid_downloader")
            urllib3_logger = logging.getLogger("urllib3")
            urllib3_logger.setLevel(logging.WARNING)
            try:
                http = urllib3.PoolManager()
                response = http.request('GET', url, preload_content=False)
                if response.status == 200:
                    #total_size = int(response.headers.get('content-length', 0))
                    block_size = 1048576
                    with open(path, "wb") as f:
                        for block_num, data in enumerate(response.stream(block_size), 1):
                            f.write(data)
                    return True
                else:
                    logger.error(f"Url response: {response.status}")
                    return False
            except HTTPError as e:
                logger.error(f"HTTP Error occurred during download: {e}")
                return False
            except URLError as e:
                logger.error(f"URL Error occurred during download: {e}")
                return False
            except Exception as e:
                logger.error(f"Exception Error occurred during download: {e}")
                return False

        status = _init_(path=path, url=url)
        return status

 
class main:
    def __init__(self, times):
        script_dir = os.path.dirname(sys.argv[0])

        log_filename = datetime.now().strftime('app_%Y-%m-%d_%H-%M-%S.log')
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s - %(name)s %(message)s', handlers=[logging.StreamHandler(), logging.FileHandler(f"{script_dir}/data/logs/{log_filename}")])
        logger = logging.getLogger("init")

        anime_json = f'{script_dir}/data/anime.json'
        as_base_url = "https://anime-sama.fr/catalogue/"
        episode_js = f'{script_dir}/data/download/episode.js'

        self.downloader = downloader(nombre_threads=4)

        while True:
            self.start(script_dir, anime_json, as_base_url, episode_js)
            self.countdown_timer(times)

    def countdown_timer(self, seconds):
        logger = logging.getLogger("timer")
        while seconds:
            hours, remainder = divmod(seconds, 3600)
            mins, secs = divmod(remainder, 60)
            timer = f'{hours:02d}:{mins:02d}:{secs:02d}'
            print(timer, end="\r")
            time.sleep(1)
            seconds -= 1
        logger.info("starting traitement")

    def start(self, script_dir, anime_json, as_base_url, episode_js):
        logger = logging.getLogger(f"Anime Traitement")
        anime_infos = self.build_url(as_base_url=as_base_url, anime_json=anime_json)
        queue = []
        if anime_infos:
            for anime_info in anime_infos:
                logger = logging.getLogger(f"anime: {anime_info[1]} saison {anime_info[2]}")
                logger.info(f"scan en cour")
                logger.info(f"url: {anime_info[0]}")

                download_path = f"{script_dir}/data/download/{anime_info[1]} s{anime_info[2]}.json"
                anime_path = f"{script_dir}/data/anime/{anime_info[1]} s{anime_info[2]}.json"

                is_download = self.find_episodejs(anime_info=anime_info, episode_js=episode_js)
                if is_download == True:
                    self.extract_link(download_path=download_path, episode_js=episode_js)

                    new_episode = self.compare_json(download_path=download_path, anime_path=anime_path)
                    if new_episode:
                        
                        queue.append((anime_info, new_episode, anime_path))

                    for numb, link in new_episode:
                        logger.info(f"!!!! nouveaux !!!! episode {numb}, {link}")
                logger.info(f"scan en terminer")

            for anime_info, new_episode, anime_path in queue:    
                self.downloader._add_to_queue(anime_info, new_episode, anime_path)
        else:
            logger.warning(f"anime.json is empty")

    
    def build_url(self, as_base_url, anime_json):
         with open(anime_json, 'r') as file:
            data = json.load(file)

            anime_info = []
            for entry in data:
                comment = entry.get("__comment")
                if comment: 
                    continue
                name = entry.get('name')
                if name == "none":
                    continue
                season = entry.get('season')
                langage = entry.get('langage')
                url = f"{as_base_url}{name}/saison{season}/{langage}/"

                anime_info.append((url, name, season, langage))

            return anime_info
        
    def find_episodejs(self, anime_info, episode_js):
        logger = logging.getLogger(f"anime: {anime_info[1]} saison {anime_info[2]}")
        response = requests.get(anime_info[0])
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            script_tag = soup.find('script', src=lambda x: x and 'episodes.js?' in x)
            if script_tag:
                script_url = script_tag['src']
                if not script_url.startswith('http'):
                    script_url = anime_info[0].rstrip('/') + '/' + script_url.lstrip('/')
                    script_response = requests.get(url=script_url, stream=True)
                    
                    if script_response.status_code == 200:
                        with open(episode_js, 'wb') as file:
                            file.write(script_response.content)
                        return True
            else:
                logger.warning(f"episode.js was not found: {script_url}")
                return False
        else:
            logger.warning(f"url not work: {anime_info[0]}")
            return False
         
    def extract_link(self, download_path, episode_js):
        logger = logging.getLogger(f"Extract Link")
        with open(episode_js, 'r') as file:
            js_content = file.read()
        
        context = js2py.EvalJs()
        context.execute(js_content)

        variables_to_check = ['eps1', 'eps2', 'eps3', 'eps4', 'eps5', 'eps6', 'eps7', 'eps8']
        domains = {"video.sibnet.ru": [], "vidmoly.to": [], "sendvid.com": []}

        def count_domain_urls(python_array, domains):
            counts = {domain: 0 for domain in domains.keys()}
            for item in python_array:
                if 'vk.com' in item:
                    continue 
                for domain in counts.keys():
                    if domain in item:
                        counts[domain] += 1
            return counts

        def is_matching_domain(url, domain):
            if '://' in url:
                url = url.split('://', 1)[1]
            extracted_domain = url.split('/', 1)[0]
            return extracted_domain == domain
        
        def number_urls(domain, url_list):
            numbered_list = []
            seen_urls = set()
            for i, url in enumerate(url_list):
                if url and url not in seen_urls and is_matching_domain(url, domain):
                    numbered_list.append(url)
                    seen_urls.add(url)
                else:
                    numbered_list.append(None)
            return numbered_list
        

        for var_name in variables_to_check:
            try:
                js_object = getattr(context, var_name)
                if isinstance(js_object, js2py.base.JsObjectWrapper):
                    js_array = list(js_object)
                else:
                    js_array = js_object
                
                if isinstance(js_array, str):
                    python_array = [js_array]
                else:
                    python_array = list(js_array)
                
                counts = count_domain_urls(python_array, domains)
                max_domain = max(counts, key=counts.get)
                if counts[max_domain] > 0:
                    domains[max_domain].extend(python_array)
            except js2py.internals.simplex.JsException as e:
                pass
        
        max_length = max(len(urls) for urls in domains.values())
        for domain in domains:
            while len(domains[domain]) < max_length:
                domains[domain].append(None)

        numbered_domains = {domain: number_urls(domain, domains[domain]) for domain in domains.keys()}
        json_output = {}
        for i in range(max_length):
            json_output[str(i + 1)] = [numbered_domains["video.sibnet.ru"][i] if i < len(numbered_domains["video.sibnet.ru"]) else None,numbered_domains["vidmoly.to"][i] if i < len(numbered_domains["vidmoly.to"]) else None,numbered_domains["sendvid.com"][i] if i < len(numbered_domains["sendvid.com"]) else None]
        
        for key in json_output:
            json_output[key] = [url if url is not None else "none" for url in json_output[key]]
        
        with open(download_path, 'w') as json_file:
            json.dump(json_output, json_file, indent=4)

    def compare_json(self, download_path, anime_path):
        with open(download_path, 'r', encoding='utf-8') as file1:
            data1 = json.load(file1)
        
        if not os.path.exists(anime_path):
            json_structure = {}
            with open(anime_path, 'w') as json_file:
                json.dump(json_structure, json_file, indent=4)

        with open(anime_path, 'r', encoding='utf-8') as file2:
            data2 = json.load(file2)
            
        new_entries = []
        
        keys2 = {int(k) for k in data2.keys() if k.isdigit()}
        
        for key in data1:
            num_key = int(key)
            if num_key not in keys2:
                new_entries.append((key, data1[key]))
        return new_entries

if __name__ == "__main__":
    main(times=3600)