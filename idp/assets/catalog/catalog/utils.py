from os import environ
import json
from jmespath import search

MODEL_FILENAME = environ['MODEL_FILENAME']


def get_model():
    with open(MODEL_FILENAME, 'r') as fh:
        return(json.load(fh))

def from_model(model, key: str):
    return search(key, model)