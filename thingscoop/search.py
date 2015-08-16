import glob
import os
import shutil
import subprocess
import sys
import tempfile
from operator import itemgetter

from progressbar import ProgressBar, Percentage, Bar, ETA

from .query import eval_query_with_labels
from .utils import extract_frames
from .utils import generate_index_path
from .utils import read_index_from_path
from .utils import save_index_to_path

def times_to_regions(times, max_total_length=None):
    if not times:
        return []
    regions = []
    current_start = times[0]
    for t1, t2 in zip(times, times[1:]):
        if t2 - t1 > 1:
            regions.append((current_start, t1 + 1))
            current_start = t2
    regions.append((current_start, times[-1] + 1))
    if not max_total_length:
        return regions
    accum = 0
    ret = []
    for index, (t1, t2) in enumerate(regions):
        if accum + (t2-t1) > max_total_length:
            ret.append((t1, t1 + max_total_length-accum))
            return ret
        else:
            ret.append((t1, t2))
            accum += t2 - t1
    return ret

def unique_labels(timed_labels):
    ret = set()
    for t, labels_list in timed_labels:
        ret.update(map(itemgetter(0), labels_list))
    return ret

def reverse_index(timed_labels, min_occurrences=2, max_length_per_label=8):
    ret = {}
    for label in unique_labels(timed_labels):
        times = []
        for t, labels_list in timed_labels:
            raw_labels = map(lambda (l, c): l, labels_list)
            if eval_query_with_labels(label, raw_labels):
                times.append(t)
        if len(times) >= min_occurrences:
            ret[label] = times_to_regions(times, max_total_length=max_length_per_label)
    return ret

def threshold_labels(timed_labels, min_confidence):
    ret = []
    for t, label_list in timed_labels:
        filtered = filter(lambda (l, c): c > min_confidence, label_list)
        if filtered:
            ret.append((t, filtered))
    return ret

def filter_out_labels(timed_labels, ignore_list):
    ret = []
    for t, label_list in timed_labels:
        filtered = filter(lambda (l, c): l not in ignore_list, label_list)
        if filtered:
            ret.append((t, filtered))
    return ret

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
        labels = classifier.classify_image(frame)
        if not len(labels):
            continue
        t = (1./sample_rate) * index
        timed_labels.append((t, labels))
    
    shutil.rmtree(temp_frame_dir)
    save_index_to_path(index_filename, timed_labels)
    
    return timed_labels

def label_videos(filenames, classifier, sample_rate=1, recreate_index=False):
    ret = {}
    for filename in filenames:
        ret[filename] = label_video(
            filename,
            classifier,
            sample_rate=sample_rate,
            recreate_index=recreate_index
        )
    return ret

def search_labels(timed_labels, query, classifier, sample_rate=1, recreate_index=False, min_confidence=0.3):
    timed_labels = threshold_labels(timed_labels, min_confidence)

    times = []
    for t, labels_list in timed_labels:
        raw_labels = map(lambda (l, c): l, labels_list)
        if eval_query_with_labels(query, raw_labels):
            times.append(t)

    return times_to_regions(times)

def search_videos(labels_by_filename, query, classifier, sample_rate=1, recreate_index=False, min_confidence=0.3):
    ret = []
    for filename, timed_labels in labels_by_filename.items():
        ret += map(lambda r: (filename, r), search_labels(
            timed_labels,
            query,
            classifier,
            sample_rate=sample_rate,
            recreate_index=recreate_index,
            min_confidence=min_confidence
        ))
    return ret

