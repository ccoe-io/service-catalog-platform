from dataclasses import dataclass, field, InitVar
from typing import List
from logger import logger
from manifest.manifest import CatalogManifest
from model.dependency import Dependencies
from model.tagoption import TagOptions
from model.product import Products
from model.portfolio import Portfolios
from model.version import Version


@dataclass
class Catalog():
    catalog_manifest: InitVar[CatalogManifest]
    dependencies: Dependencies = None
    tag_options: TagOptions = None
    products: Products = None
    portfolios: Portfolios = None
    versions: List[Version] = field(default_factory=list)

    def __post_init__(self, catalog_manifest: CatalogManifest) -> None:
        cm = catalog_manifest
        self.dependencies = Dependencies(cm.Dependencies)
        self.tag_options = TagOptions(cm)
        self.products = Products(cm.Products)
        self.portfolios = Portfolios(cm.Portfolios)

        for product in self.products.items:
            product.build_tag_options_assoc(self.tag_options)
            product.build_portfolios_assoc(self.portfolios)
            product.build_assoc_accounts(self.portfolios)

        for portfolio in self.portfolios.items:
            portfolio.build_tag_options_assoc(self.tag_options)
        
        for product in self.products.items:
            self.versions += product.versions.items

        for dependency in self.dependencies.items:
            dependency.build_assoc_accounts(self.products)