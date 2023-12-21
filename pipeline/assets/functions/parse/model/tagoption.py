import hashlib
from typing import List
from dataclasses import dataclass, field, InitVar
from logger import logger
from manifest.manifest import CatalogManifest


def generate_id(*args):
    m = hashlib.md5()
    _str = ''
    for arg in args:
        _str += arg
    m.update(_str.encode('utf-8'))
    return m.hexdigest()


@dataclass
class TagOption():
    key: str
    value: str
    mid: str = None

    def __post_init__(self) -> None:
        self.mid = generate_id(self.key, self.value)


@dataclass
class TagOptions():
    manifest: InitVar[CatalogManifest] = field(repr=False)
    items: List[TagOption] = field(default_factory=list)

    def __post_init__(self, manifest: CatalogManifest) -> None:
        self._manifest = manifest
        self._build()

    def _build(self):
        tag_options_manifest = []
        for pm in self._manifest.Products:
            for tom in pm.TagOptions:
                tag_options_manifest.append(tom)
        for pm in self._manifest.Portfolios:
            for tom in pm.TagOptions:
                tag_options_manifest.append(tom)
        # logger.debug(tag_options_manifest)
        for tom in tag_options_manifest:
            for value in tom.Values:
                # logger.debug('tag-option: {} id:{}'.format((tom.Key, value), generate_id(tom.Key, value)))
                if generate_id(tom.Key, value) not in self.get_ids():
                    self.items.append(TagOption(tom.Key, value))

    def get_ids(self):
        return [item.mid for item in self.items]

    def get_by_key_value(self, key: str, value: str):
        for to in self.items:
            if generate_id(key, value) == to.mid:
                return to