import glob
import os
import shutil
import subprocess
import sys
import tempfile
from progressbar import ProgressBar, Percentage, Bar, ETA

from .query import eval_query_with_labels
from .utils import extract_frames
from .utils import generate_index_path
from .utils import read_index_from_path
from .utils import save_index_to_path

def label_frame(filename, classifier):
    return map(lambda (l, c): l, classifier.classify_image(filename))

def label_video(filename, classifier, sample_rate=1, recreate_index=False):
    index_filename = generate_index_path(filename, classifier.model)
    
    if os.path.exists(index_filename) and not recreate_index:
        return read_index_from_path(index_filename)
    
    temp_frame_dir, frames = extract_frames(filename, sample_rate=sample_rate)

    timed_labels = []

    widgets=["Labeling {}: ".format(filename), Percentage(), ' ', Bar(), ' ', ETA()]
    pbar = ProgressBar(widgets=widgets, maxval=len(frames)).start()

    for index, frame in enumerate(frames):
        pbar.update(index)
        labels = label_frame(frame, classifier)
        if not len(labels):
            continue
        t = (1./sample_rate) * index
        timed_labels.append((t, labels))
    
    shutil.rmtree(temp_frame_dir)
    save_index_to_path(index_filename, timed_labels)
    
    return timed_labels

def search_video(filename, query, classifier, sample_rate=1, recreate_index=False):
    timed_labels = label_video(
        filename,
        classifier,
        sample_rate=sample_rate,
        recreate_index=recreate_index
    )

    inside_range = False
    range_start = None
    range_end = False

    ret = []
    for t, labels in timed_labels:
        success = eval_query_with_labels(query, labels)
        
        if not inside_range and success:
            range_start = t
            range_end = t
            inside_range = True
                
        elif inside_range and not success:
            range_end = t
            inside_range = False
            ret.append((range_start, range_end))
    
    if inside_range:
        ret.append((range_start, range_end))

    return ret

def search_videos(filenames, query, classifier, sample_rate=1, recreate_index=False):
    ret = []
    for filename in filenames:
        ret.extend(map(lambda r: (filename, r), search_video(
            filename,
            query,
            classifier,
            sample_rate=sample_rate,
            recreate_index=recreate_index
        )))
    return ret

