import os
from typing import List, Any
from dataclasses import dataclass, field, InitVar
from logger import logger
from utils import render_role_template, nested_stack_resource
from manifest.manifest import ProductManifest
from model.version import Versions
from model.artifact import Template
from model.tagoption import TagOption
from model.portfolio import Portfolio

REGION = os.environ['CATALOG_ARTIFACTS_BUCKET_REGION']
ARTIFACTS_BUCKET = os.environ['CATALOG_ARTIFACTS_BUCKET']


@dataclass
class Product():
    manifest: InitVar[ProductManifest]
    Name: str = None
    Description: str = None
    Distributor: str = None
    Owner: str = None
    SupportDescription: str = None
    SupportEmail: str = None
    SupportUrl: str = None
    mid: str = None
    local_base_path: str = None
    launch_role_name: str = None
    artifact_template: Template = None
    artifact_launch_role: Template = None
    versions: Versions = None
    assoc_tag_options: List[TagOption] = field(default_factory=list)
    assoc_portfolios: List[Portfolio] = field(default_factory=list)
    assoc_dependencies: List[str] = field(default_factory=list)
    assoc_accounts: List[str] = field(default_factory=list)

    def __post_init__(self, manifest: ProductManifest) -> None:
        self._manifest = manifest
        self.Name=self._manifest.Name
        self.Description=self._manifest.Description
        self.Distributor=self._manifest.Distributor
        self.Owner=self._manifest.Owner
        self.SupportDescription=self._manifest.SupportDescription
        self.SupportEmail=self._manifest.SupportEmail
        self.SupportUrl=self._manifest.SupportUrl
        self.mid = self._manifest.Id
        self.local_base_path = os.path.dirname(self._manifest.path)
        self.launch_role_name = (f'{self._manifest.ExistLaunchRoleName}' or
            f'sc-launch-{self._manifest.Id}') + '-' + REGION
        self.launch_role_exists = True if self._manifest.ExistLaunchRoleName else False
        pm = self._manifest

        self.assoc_dependencies = self._manifest.Dependencies

        # Artifacts
        s3_prefix = f'products/{self.mid}'

        template_file = os.path.join(self.local_base_path, pm.Artifacts.Template)
        self.artifact_template = Template(
            ARTIFACTS_BUCKET,
            s3_prefix,
            template_file
        )
        self.artifact_template.upload()

        if not self.launch_role_exists:
            role_policies_file = os.path.join(self.local_base_path, pm.Artifacts.LaunchRolePermissions)
            if os.path.isfile(role_policies_file):
                role_file = render_role_template(self.launch_role_name, role_policies_file)
                self.artifact_launch_role = Template(
                    ARTIFACTS_BUCKET,
                    s3_prefix,
                    role_file
                )
                self.artifact_launch_role.upload()

        # versions is list of version objects
        self.versions = Versions(self.mid)
        if not self.versions.exists(self.artifact_template.mid):
            self.versions.create(
                self.artifact_template.mid,
                self.artifact_template.s3url,
                option=self._manifest.VersionOption,
                description=self._manifest.VersionDescription
            )
        # self.versions.update_metadata(
        #     self.artifact_template.mid,
        #     description=self._manifest.VersionDescription)
        self.versions.activate_versions(self._manifest.Versions)

    def build_tag_options_assoc(self, tag_options):
        for tom in self._manifest.TagOptions:
            for value in tom.Values:
                to = tag_options.get_by_key_value(tom.Key, value)
                if to:
                    self.assoc_tag_options.append(to.mid)

    def build_portfolios_assoc(self, portfolios):
        for portfolio in portfolios.items:
            if self.mid in portfolio.assoc_products:
                self.assoc_portfolios.append(portfolio.mid)

    def build_assoc_accounts(self, portfolios):
        for portfolio in portfolios.items:
            if portfolio.mid in self.assoc_portfolios:
                self.assoc_accounts += portfolio.accounts

    def render_nested_stack_launch_role_resource(self) -> dict:
        return (
            nested_stack_resource(
                self.mid+'LaunchRole',
                self.artifact_launch_role.s3url
            )
        )

@dataclass
class Products():
    manifest: InitVar[List[ProductManifest]] = field(repr=False)
    items: List[Product] = field(default_factory=list)

    def __post_init__(self, manifest: List[ProductManifest]) -> None:
        self._manifest = manifest
        self._build()

    def _build(self) -> None:
        for pm in self._manifest:
            self.items.append(Product(pm))

    def filter_by_attr(self, attr_key: str, attr_value: Any) -> Product:
        for item in self.items:
            if getattr(item, attr_key) == attr_value:
                return item
