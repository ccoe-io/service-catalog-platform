from typing import List, Dict
from dataclasses import dataclass, field, InitVar
from logger import logger
from manifest.manifest import PortfolioManifest
from model.tagoption import TagOption


@dataclass
class Portfolio():
    manifest: InitVar[PortfolioManifest] = field(repr=False)
    mid: str = None
    assoc_tag_options: List[TagOption] = field(default_factory=list)
    assoc_products: List[str] = field(default_factory=list)
    accounts: List[str] = field(default_factory=list)
    shares: Dict[str, list] = field(default_factory=dict)
    principals: Dict[str, str] = field(default_factory=dict)
    Name: str = None
    Description: str = None
    ProviderName: str = None

    def __post_init__(self, manifest: PortfolioManifest) -> None:
        self._manifest = manifest
        self.mid = manifest.Id
        self.Name = manifest.Name
        self.Description = manifest.Description
        self.ProviderName = manifest.ProviderName

        self.assoc_products = self._manifest.Products
        self.build_shares()
        self.principals = self._manifest.Principals

    def build_tag_options_assoc(self, tag_options):
        for tom in self._manifest.TagOptions:
            for value in tom.Values:
                to = tag_options.get_by_key_value(tom.Key, value)
                if to:
                    self.assoc_tag_options.append(to.mid)
    
    def build_shares(self):
        for share in self._manifest.Shares:
            if share.SelectorType == 'AccountsIds':
                self.shares.update({"AccountsIds": share.Values})
            elif share.SelectorType == 'OrgUnitsIds':
                self.shares.update({"OrgUnitsIds": share.Values})
            elif share.SelectorType == 'OrgIds':
                self.shares.update({"OrgIds": share.Values})


@dataclass
class Portfolios():
    manifest: InitVar[List[PortfolioManifest]] = field(repr=False)
    items: List[Portfolio] = field(default_factory=list)

    def __post_init__(self, manifest: List[PortfolioManifest]) -> None:
        self._manifest = manifest
        self._build()
    
    def _build(self) -> None:
        for pm in self._manifest:
            self.items.append(Portfolio(pm))