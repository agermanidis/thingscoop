import glob
import json
import os
import re
import subprocess
import tempfile
import textwrap
from moviepy.editor import VideoFileClip, TextClip, ImageClip, concatenate_videoclips
from pattern.en import wordnet
from termcolor import colored
from PIL import Image, ImageDraw, ImageFont

def create_title_frame(title, dimensions, fontsize=60):
    para = textwrap.wrap(title, width=30)
    im = Image.new('RGB', dimensions, (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    font = ImageFont.truetype('resources/Helvetica.ttc', fontsize)
    total_height = sum(map(lambda l: draw.textsize(l, font=font)[1], para))
    current_h, pad = (dimensions[1]/2-total_height/2), 10
    for line in para:
        w, h = draw.textsize(line, font=font)
        draw.text(((dimensions[0] - w) / 2, current_h), line, font=font)
        current_h += h + pad
    f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    im.save(f.name)
    return f.name

def get_video_dimensions(filename):
    p = subprocess.Popen(['ffprobe', filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _, out = p.communicate()
    for line in out.split('\n'):
        if re.search('Video: ', line):
            match = re.findall('[1-9][0-9]*x[1-9][0-9]*', line)[0]
            return tuple(map(int, match.split('x')))

def extract_frames(filename, sample_rate=1):
    dest_dir = tempfile.mkdtemp()
    dest = os.path.join(dest_dir, "%10d.png")
    subprocess.check_output(["ffmpeg", "-i", filename, "-vf", "fps="+str(sample_rate), dest])
    glob_pattern = os.path.join(dest_dir, "*.png")
    return dest_dir, glob.glob(glob_pattern)

def generate_index_path(filename, model):
    name, ext = os.path.splitext(filename)
    return "{name}_{model_name}.json".format(name=name, model_name=model.name)

def read_index_from_path(filename):
    return json.load(open(filename))

def save_index_to_path(filename, timed_labels):
    json.dump(timed_labels, open(filename, 'w'), indent=4)

def create_supercut(regions):
    subclips = []
    filenames = set(map(lambda (filename, _): filename, regions))
    video_files = {filename: VideoFileClip(filename) for filename in filenames}
    for filename, region in regions:
        subclip = video_files[filename].subclip(*region)
        subclips.append(subclip)
    if not subclips: return None
    return concatenate_videoclips(subclips)

def label_as_title(label):
    return label.replace('_', ' ').upper()

def create_compilation(filename, index):
    dims = get_video_dimensions(filename)
    subclips = []
    video_file = VideoFileClip(filename)
    for label in sorted(index.keys()):
        label_img_filename = create_title_frame(label_as_title(label), dims)
        label_clip = ImageClip(label_img_filename, duration=2)
        os.remove(label_img_filename)
        subclips.append(label_clip)
        for region in index[label]:
            subclip = video_file.subclip(*region)
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

def merge_values(d):
    ret = []
    for lst in d.values():
        ret += lst
    return ret

