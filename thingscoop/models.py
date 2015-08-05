import glob
import os
import requests
import shutil
import tempfile
import urlparse
import yaml
import zipfile
import urllib
from pattern.en import wordnet
from progressbar import ProgressBar, Percentage, Bar, ETA, FileTransferSpeed

from .utils import get_hypernyms

THINGSCOOP_DIR = os.path.join(os.path.expanduser("~"), ".thingscoop")
CONFIG_PATH = os.path.join(THINGSCOOP_DIR, "config.yml")

DEFAULT_CONFIG = {
    'repo_url': 'https://s3.amazonaws.com/haystack-models/',
    'active_model': 'googlenet_imagenet'
}

class CouldNotFindModel(Exception):
    pass

class Model(object):
    def __init__(self, name, model_dir):
        self.name = name
        self.model_dir = model_dir
        self.info = yaml.load(open(os.path.join(model_dir, "info.yml")))

    def get(self, k):
        return self.info.get(k)

    def model_path(self):
        return os.path.join(self.model_dir, self.info['pretrained_model_file'])

    def deploy_path(self):
        return os.path.join(self.model_dir, self.info['deploy_file'])

    def label_path(self):
        return os.path.join(self.model_dir, self.info['labels_file'])

    def bet_path(self):
        if 'bet_file' not in self.info: return None
        return os.path.join(self.model_dir, self.info['bet_file'])

    def labels(self, with_hypernyms=False):
        ret = map(str.strip, open(self.label_path()).readlines())
        if with_hypernyms:
            for label in list(ret):
                ret.extend(get_hypernyms(label))
        return ret

def read_config():
    if not os.path.exists(CONFIG_PATH):
        write_config(DEFAULT_CONFIG)
    return yaml.load(open(CONFIG_PATH))

def write_config(config):
    if not os.path.exists(THINGSCOOP_DIR):
        os.makedirs(THINGSCOOP_DIR)
    yaml.dump(config, open(CONFIG_PATH, 'wb'))

def get_repo_url():
    return read_config()['repo_url']

def get_active_model():
    return read_config()['active_model']

def get_model_url(model):
    return get_repo_url() + model + ".zip"

def get_model_local_path(model):
    return os.path.join(THINGSCOOP_DIR, "models", model)

def set_config(k, v):
    config = read_config()
    config[k] = v
    write_config(config)

def model_in_cache(model):
    return os.path.exists(get_model_local_path(model))

def get_models_path():
    return os.path.join(THINGSCOOP_DIR, "models")

def get_all_models():
    return yaml.load(requests.get(urlparse.urljoin(get_repo_url(), "info.yml")).text)

def info_model(model):
    models = get_all_models()
    for model_info in models:
        if model_info['name'] == model:
            return model_info

def use_model(model):
    download_model(model)
    set_config("active_model", model)

def remove_model(model):
    path = get_model_local_path(model)
    shutil.rmtree(path)

def clear_models():
    for model in get_downloaded_models():
        remove_model(model)

def read_model(model_name):
    if not model_in_cache(model_name):
        raise CouldNotFindModel, "Could not find model {}".format(model_name)
    return Model(model_name, get_model_local_path(model_name))

def get_downloaded_models():
    return map(os.path.basename, glob.glob(os.path.join(get_models_path(), "*")))

progress_bar = None
def download_model(model):
    if model_in_cache(model): return
    model_url = get_model_url(model)
    tmp_zip = tempfile.NamedTemporaryFile(suffix=".zip")
    prompt = "Downloading model {}".format(model)
    def cb(count, block_size, total_size):
        global progress_bar
        if not progress_bar:
            widgets = [prompt, Percentage(), ' ', Bar(), ' ', FileTransferSpeed(), ' ', ETA()]
            progress_bar = ProgressBar(widgets=widgets, maxval=int(total_size)).start()
        progress_bar.update(min(total_size, count * block_size))
    urllib.urlretrieve(model_url, tmp_zip.name, cb)
    z = zipfile.ZipFile(tmp_zip)
    out_path = get_model_local_path(model)
    try:
        os.mkdir(out_path)
    except:
        pass
    for name in z.namelist():
        if name.startswith("_"): continue
        z.extract(name, out_path)

