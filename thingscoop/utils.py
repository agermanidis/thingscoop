import glob
import os
import re
import subprocess
import tempfile
from moviepy.editor import VideoFileClip, concatenate_videoclips
from pattern.en import wordnet
from termcolor import colored

def extract_frames(filename, sample_rate=1):
    dest_dir = tempfile.mkdtemp()
    dest = os.path.join(dest_dir, "%10d.png")
    subprocess.check_output(["ffmpeg", "-i", filename, "-vf", "fps="+str(sample_rate), dest])
    glob_pattern = os.path.join(dest_dir, "*.png")
    return dest_dir, glob.glob(glob_pattern)

def generate_index_path(filename, model):
    name, ext = os.path.splitext(filename)
    return "{name}_{model_name}.txt".format(name=name, model_name=model.name)

def read_index_from_path(filename):
    lines = open(filename).readlines()
    ret = []
    for line in lines:
        parts = line.strip().split(' ')
        t = float(parts[0])
        if not parts[1:]: continue
        labels = ' '.join(parts[1:]).split(',')
        ret.append((t, labels))
    return ret

def save_index_to_path(filename, timed_labels):
    lines = []
    for t, labels in timed_labels:
        lines.append("%f %s\n" % (t, ",".join(labels)))
    open(filename, 'wb').writelines(lines)

def create_supercut(regions):
    subclips = []
    filenames = set(map(lambda (filename, _): filename, regions))
    video_files = {filename: VideoFileClip(filename) for filename in filenames}
    for filename, region in regions:
        subclip = video_files[filename].subclip(*region)
        subclips.append(subclip)
    if not subclips: return None
    return concatenate_videoclips(subclips)

def search_labels(r, labels):
    r = re.compile(r)
    for label in labels:
        if not r.search(label):
            continue
        current_i = 0
        ret = ''
        for m in r.finditer(label):
            ret += label[current_i:m.start()]
            ret += colored(label[m.start():m.end()], 'red', attrs=['bold'])
            current_i = m.end()
        ret += label[m.end():]
        print ret

def get_hypernyms(label):
    synsets = wordnet.synsets(label)
    if not synsets: return []
    return map(lambda s: s.synonyms[0], synsets[0].hypernyms(True))

