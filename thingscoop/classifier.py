import cPickle
import caffe
import cv2
import glob
import logging
import numpy
import os

class ImageClassifier(object):
    def __init__(self, model, gpu_mode=False):
        self.model = model
        
        kwargs = {}

        if self.model.get("image_dims"):
            kwargs['image_dims'] = tuple(self.model.get("image_dims"))

        if self.model.get("channel_swap"):
            kwargs['channel_swap'] = tuple(self.model.get("channel_swap"))

        if self.model.get("raw_scale"):
            kwargs['raw_scale'] = float(self.model.get("raw_scale"))

        if self.model.get("mean"):
            kwargs['mean'] = numpy.array(self.model.get("mean"))
        
        self.net = caffe.Classifier(
            model.deploy_path(),
            model.model_path(),
            **kwargs
        )
        
        self.confidence_threshold = 0.1
        
        if gpu_mode:
            caffe.set_mode_gpu()
        else:
            caffe.set_mode_cpu()

        self.labels = numpy.array(model.labels())

        if self.model.bet_path():
            self.bet = cPickle.load(open(self.model.bet_path()))
            self.bet['words'] = map(lambda w: w.replace(' ', '_'), self.bet['words'])
        else:
            self.bet = None
        
        self.net.forward()

    def classify_image(self, filename):
        image = caffe.io.load_image(open(filename))
        scores = self.net.predict([image], oversample=True).flatten()

        if self.bet:
            expected_infogain = numpy.dot(self.bet['probmat'], scores[self.bet['idmapping']])
            expected_infogain *= self.bet['infogain']
            infogain_sort = expected_infogain.argsort()[::-1]
            results = [
                (self.bet['words'][v], float(expected_infogain[v]))
                for v in infogain_sort
                if expected_infogain[v] > self.confidence_threshold
            ]

        else:
            indices = (-scores).argsort()
            predictions = self.labels[indices]
            results = [
                (p, float(scores[i]))
                for i, p in zip(indices, predictions)
                if scores[i] > self.confidence_threshold
            ]

        return results

