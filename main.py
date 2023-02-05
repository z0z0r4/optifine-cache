import requests
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
import re
import json
import os
import hashlib

# proxy = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
proxy = None

def file_hash(file_path: str) -> str:
    h = hashlib.md5()
    with open(file_path, 'rb') as f:
        while b := f.read(1024):
            h.update(b)
    return h.hexdigest()

def get_file(url: str, name: str):
    _i = 0
    while _i < 3:
        try:
            resp = requests.get(url, stream=True, proxies=proxy, timeout=10)
            with open(name, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=1024):
                    f.write(chunk)
            return file_hash(name)
        except TimeoutError:
            print(f"{url} TimeoutError")
        except Exception as e:
            print(f"{url} {e}")
        _i += 1


def get_mcversion_from_url(url: str):
    return re.match("OptiFine_(.+?)_(.+?).jar", re.match(r"http://optifine.net/adloadx\?f=(.+?\.jar)", url).group(1).replace("preview_", "")).group(1)

def get_optifine_type_from_url(url: str):
    if "pre" in url.split("_")[-1].split(".")[0]:
        return "pre"
    else:
        return "release"

def get_opt_jar_name_from_url(url: str):
    return re.match(r"http://optifine.net/adloadx\?f=(.+?\.jar)", url).group(1)


def get_optifine_info():
    optifine_page_url = "https://optifine.net/downloads"
    res = requests.get(optifine_page_url)
    soup = BeautifulSoup(res.text, "html.parser")
    downloads = soup.find(attrs={'class': 'downloads'})
    opt_obj_list, results = [], {}
    opt_obj_list.extend(downloads.find_all(
        "tr", attrs={"class": "downloadLine downloadLineMain"}))
    opt_obj_list.extend(downloads.find_all(
        "tr", attrs={"class": "downloadLine downloadLineMore"}))
    opt_obj_list.extend(downloads.find_all(
        "tr", attrs={"class": "downloadLine downloadLinePreview"}))
    for opt_obj in opt_obj_list:
        opt_raw_ver = opt_obj.find("td", attrs={"class": "colFile"}).text
        opt_dl_url = opt_obj.find(
            "td", attrs={"class": "colMirror"}).find("a").get("href")
        opt_forge_ver = opt_obj.find("td", attrs={"class": "colForge"}).text
        opt_release_date = opt_obj.find("td", attrs={"class": "colDate"}).text
        opt_info = {
            "version": opt_raw_ver,
            "download_url": opt_dl_url,
            "forge_version": opt_forge_ver,
            "release_date": opt_release_date,
            "mc_version": get_mcversion_from_url(opt_dl_url),
            "type": get_optifine_type_from_url(opt_dl_url)
        }
        results[get_opt_jar_name_from_url(opt_dl_url)[:-4]] = opt_info

    return results

def process_optifine_info(obj: dict) -> dict:
    name = os.path.join("cache", get_opt_jar_name_from_url(obj["download_url"]))
    res = requests.get(obj["download_url"])
    session = re.findall("x=(.+?)'", res.text)[0]
    url = obj["download_url"].replace("http://optifine.net/adloadx","https://optifine.net/downloadx") + "&x=" + session
    hash = get_file(url, name=name)
    obj["hash"] = hash
    return_obj = {get_opt_jar_name_from_url(obj["download_url"])[:-4]: obj}
    print(return_obj)
    return return_obj

def main():
    opt_info = {}
    if os.path.exists("results.json"):
        with open("results.json") as f:
            opt_info = json.load(f)
    new_opt_info = get_optifine_info()
    opt_info.update(new_opt_info)
    results = []
    tasks = []
    if not os.path.exists("cache"):
        os.mkdir("cache")
    with ThreadPoolExecutor(max_workers=64) as executor:
        for obj in opt_info:
            tasks.append(executor.submit(process_optifine_info, opt_info[obj]))
        for result in tasks:
            opt_info.update(result.result())
    with open("results.json", "w") as f:
        json.dump(results, f, indent=4)

if __name__ == "__main__":
    main()
