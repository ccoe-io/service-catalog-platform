from datetime import datetime
from typing import List
from dataclasses import dataclass, field
from logger import logger
from aws.dynamodb import versions_table


@dataclass
class Version():
    product_id: str
    mid: str
    label: str
    major: str
    minor: str
    description: str
    template_url: str
    active: bool
    created: str


@dataclass
class Versions():
    product_id: str
    items: List[Version] = field(default_factory=list)
    latest: Version = None

    def __post_init__(self) -> None:
        self.load()
        if self.items:
            self.items.sort(key=lambda x: x.created, reverse=True)
        self.latest = self.get_latest()

    def get_latest(self):
        if self.items:
            return self.items[0]

    def exists(self, s3version) -> bool:
        for ver in self.items:
            if ver.mid == s3version:
                return True
        return False

    def create(self, s3version, template_url, option=False, description=None) -> None:
        if self.exists(s3version):
            return

        label =  Label('v1.0')
        if self.latest:
            latest_label = Label(self.latest.label)
            if option == 'Major':
                label = Label(latest_label.next_major())
            elif option == 'Minor':
                label = Label(latest_label.next_minor())
            elif option == 'Override':
                label = latest_label
            else:
                raise(f'Unknown version option {option}')

        ver = Version(
            product_id=self.product_id,
            label=label.label,
            major=label.major,
            minor=label.minor,
            description=description,
            mid=s3version,
            template_url=template_url,
            active = False,
            created = int(datetime.timestamp(datetime.now()))
        )
        self.items.append(ver)
        self.items.sort(key=lambda x: x.created, reverse=True)

    def activate_versions(self, desired_versions_manifest):
        for item in self.items:
            item.active = False
        for ver in desired_versions_manifest:
            if ver == 'THIS':
                self.items[0].active = True
            elif 'THIS-' in ver:
                ind = int(ver.split('THIS-')[-1])
                try:
                    self.items[ind].active = True
                except IndexError:
                    pass
            elif 'v' in ver:
                for version in self.items:
                    if ver == version.label:
                        version.active = True

    # load from table
    def load(self) -> list:
        _vers = versions_table.get_versions_product(self.product_id)
        for _ver in _vers:
            self.items.append(Version(**_ver))

    # update table
    def save(self):
        pass


class Label():

    def __init__(self, label):
        self.label = label
        self._minor = None
        self._major = None

    @property
    def minor(self):
        if not self._minor:
            if self.label:
                self._minor = self.label.split('.')[-1]
        return self._minor

    @property
    def major(self):
        if not self._major:
            if self.label:
                self._major = self.label.split('.')[0].lstrip('v')
        return self._major

    def next_major(self):
        return 'v{}.{}'.format(int(self.major)+1, 0)

    def next_minor(self):
        return 'v{}.{}'.format(
            int(self.major),
            int(self.minor)+1
        )

