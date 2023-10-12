import os
from typing import List, Any, Dict
from dataclasses import dataclass, field, InitVar
from logger import logger
from utils import nested_stack_resource
from manifest.manifest import DependencyManifest
from model.artifact import Template
from model.portfolio import Portfolios
from model.product import Products

ARTIFACTS_BUCKET = os.environ['CATALOG_ARTIFACTS_BUCKET']


@dataclass
class Dependency():
    manifest: InitVar[DependencyManifest]
    Owner: str = None
    mid: str = None
    parameters: Dict[str, str] = field(default_factory=dict)
    prerequisites: List[str] = field(default_factory=list)
    template: str = None
    artifact: Template = None
    local_base_path: str = None
    assoc_accounts: List[str] = field(default_factory=list)

    def __post_init__(self, manifest: DependencyManifest) -> None:
        self._manifest = manifest
        self.Owner=self._manifest.Owner
        self.mid = self._manifest.Id
        self.parameters = self._manifest.Parameters
        self.prerequisites = self._manifest.Prerequisites
        self.template = self._manifest.Template
        self.local_base_path = os.path.dirname(self._manifest.path)

        self.artifact = Template(
            ARTIFACTS_BUCKET,
            'dependencies/{}'.format(self.mid),
            os.path.join(self.local_base_path, self.template)
        )
        self.artifact.package()
        self.artifact.upload()

    def build_assoc_accounts(self, products: Products):
        for product in products.items:
            if self.mid in product.assoc_dependencies:
                self.assoc_accounts += product.assoc_accounts
        self.assoc_accounts = list(set(self.assoc_accounts))

    def render_nested_stack_resource(self) -> dict:
        for key, value in self.parameters.items():
            if value.startwith('Output '):
                new_value = { "Fn::GetAtt" : value.lstrip('Output ') }
                self.parameters[key] = new_value
        return nested_stack_resource(
            self.mid, self.artifact.s3url, parameters=self.parameters, depends_on=self.prerequisites
        )

@dataclass
class Dependencies():
    manifest: InitVar[List[DependencyManifest]] = field(repr=False)
    items: List[Dependency] = field(default_factory=list)

    def __post_init__(self, manifest: List[DependencyManifest]) -> None:
        self._manifest = manifest
        self._build()

    def _build(self) -> None:
        for pm in self._manifest:
            self.items.append(Dependency(pm))
