import cv2
import datetime
import math
import numpy
import random
import re
import subprocess
import sys
import caffe
import tempfile

def duration_string_to_timedelta(s):
    [hours, minutes, seconds] = map(int, s.split(':'))
    seconds = seconds + minutes * 60 + hours * 3600
    return datetime.timedelta(seconds=seconds)

def get_video_duration(path):
    result = subprocess.Popen(["ffprobe", path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    matches = [x for x in result.stdout.readlines() if "Duration" in x]
    duration_string = re.findall(r'Duration: ([0-9:]*)', matches[0])[0]
    return math.ceil(duration_string_to_timedelta(duration_string).seconds)

def get_current_position(c):
    return int(c.get(cv2.cv.CV_CAP_PROP_POS_MSEC)/1000)

def add_text_to_frame(frame, text):
    ret, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_PLAIN, 1, 1)
    ret = (ret[0] + 20, ret[1] + 20)
    cv2.rectangle(frame, (0,0), ret, (0, 0, 0), cv2.cv.CV_FILLED)
    cv2.putText(frame, text, (5, 20), cv2.FONT_HERSHEY_PLAIN, 1, (255, 255, 255))

def format_classification(result):
    str_list = []
    for label, confidence in result:
        str_list.append("{0} ({1})".format(label, confidence))
    return ', '.join(str_list)

def preview(filename, classifier):
    cv2.namedWindow('video')

    duration = int(get_video_duration(filename))

    def trackbar_change(t):
        cap.set(cv2.cv.CV_CAP_PROP_POS_MSEC, t*1000)

    trackbar_prompt = 'Current position:'
    cv2.createTrackbar(trackbar_prompt, 'video', 0, duration, trackbar_change)

    cap = cv2.VideoCapture(filename)

    classification_result = None
    previous_time_in_seconds = None
    current_pos = 0

    tmp = tempfile.NamedTemporaryFile(suffix=".png")    
    
    while cap.isOpened():
        ret, frame = cap.read()

        cv2.imwrite(tmp.name, frame)

        if ret:
            current_pos = get_current_position(cap)

            if current_pos != previous_time_in_seconds:
                previous_time_in_seconds = current_pos
                classification_result = classifier.classify_image(tmp.name)
            
            if classification_result:
                add_text_to_frame(frame, format_classification(classification_result))

            cv2.imshow('video', frame)
        
        cv2.setTrackbarPos(trackbar_prompt, 'video', current_pos)
    
        k = cv2.waitKey(1) & 0xFF
        if k == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

