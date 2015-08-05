import re
from pypeg2 import *
from pattern.en import wordnet

from .utils import get_hypernyms

class NoSuchLabelError(Exception):
    pass

class Q(object):
    def evaluate(self, labels):
        return self.content.evaluate(labels)

class Label(object):
    grammar = attr("name", re.compile(r"[A-z][A-z\- ]+[A-z]"))

    def evaluate(self, labels):
        for label in labels:
            if label == self.name or self.name in get_hypernyms(label):
                return True
        return False

class UnaryOp(object):
    grammar = (attr("operator", re.compile("!")),
               attr("content", Label))

    def evaluate(self, labels):
        return not self.content.evaluate(labels)

class ParentheticalQ(List):
    grammar = (re.compile("\("),
               attr("content", Q),
               re.compile("\)"))

    def evaluate(self, labels):
        return self.content.evaluate(labels)

class BinaryOp(object):
    grammar = (attr("lh", [ParentheticalQ, UnaryOp, Label]),
               attr("op", re.compile("(&&|\|\|)")),
               attr("rh", Q))

    def evaluate(self, labels):
        lv = self.lh.evaluate(labels)
        rv = self.rh.evaluate(labels)

        if self.op == '||': return lv or rv
        else: return lv and rv

Q.grammar = (
    maybe_some(whitespace),
    attr("content", [BinaryOp, ParentheticalQ, UnaryOp, Label]),
    maybe_some(whitespace)
)

def get_labels(parsed_q):
    if type(parsed_q) == Label:
        return [parsed_q.name]
    if type(parsed_q) == BinaryOp:
        return get_labels(parsed_q.lh) + get_labels(parsed_q.rh)
    return get_labels(parsed_q.content)

def validate_query(q, all_labels):
    parsed_q = parse(q, Q)
    for label in get_labels(parsed_q):
        if label not in all_labels:
            raise NoSuchLabelError, "Label \"{}\" does not exist.".format(label)

def eval_query_with_labels(q, labels):
    parsed_q = parse(q, Q)
    return parsed_q.evaluate(labels)

def filename_for_query(q):
    parsed_q = parse(q, Q)
    labels = get_labels(parsed_q)
    return '_'.join(labels).replace(' ', '_')
        
