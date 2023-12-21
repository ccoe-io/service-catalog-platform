from dataclasses import dataclass, field
from datafiles import datafile
from typing import List, Dict


# class ValidationError(Exception):

#     def __init__(self, message: str) -> None:
#         self.message = message
#         super().__init__(self.message)


# def validate_file_existance(file_path: str) -> None:
#     try:
#         with open(file_path):
#             pass
#     except FileNotFoundError:
#         raise ValidationError(f'\nError: file {file_path} not exist')


# class CustomTypeABC():

#     def __init__(self) -> None:
#         self._validate()

#     @abc.abstractmethod
#     def _validate(self):
#         raise NotImplementedError
        

# class FilePath(CustomTypeABC):

#     def __init__(self, path) -> None:
#         self.path = path
#         super().__init__()

#     def _validate(self):
#         validate_file_existance(self.path)

### Common Manifest Objects
@dataclass
class TagOption():
    Key: str
    Values: List[str]


@dataclass
class Selector():
    SelectorType: str
    Values: List[str]


### Product Manifest
@dataclass
class ArtifactsDC():
    Template: str
    LaunchRolePermissions: str
    EmailNotificationTemplate: str


def default_versions():
    return ['THIS']


@datafile('{self.path}', manual=True)
class ProductManifest():
    path: str
    Id: str = None
    Name: str = None
    Description: str = 'No description is noted'
    Distributor: str = 'No distributor is specified'
    Owner: str = 'No Owner is specified'
    SupportDescription: str = 'No support description is noted'
    SupportEmail: str = 'No support email is noted'
    SupportUrl: str = 'No support url is noted'
    TagOptions: List[TagOption] = field(default_factory=list)
    ExistLaunchRoleName: str = None
    Artifacts: ArtifactsDC = None
    VersionDescription: str = 'No version description is noted'
    VersionOption: str = 'Minor'
    Versions: List[str] = field(default_factory=default_versions)
    Dependencies: List[str] = field(default_factory=list)
    

# Portfolio Manifest
@datafile('{self.path}', manual=True)
class PortfolioManifest():
    path: str
    Id: str = None
    Name: str = None
    Description: str = 'No description is noted'
    ProviderName: str = 'No provider name is specified'
    TagOptions: List[TagOption] = field(default_factory=list)
    Principals: List[Selector] = field(default_factory=list)
    Products: List[str] = field(default_factory=list)
    Shares: List[Selector] = field(default_factory=list)


# Dependencies Manifest
@datafile('{self.path}', manual=True)
class DependencyManifest():
    path: str
    Id: str = None
    Template: str = 'template.yml'
    Owner: str = None
    Parameters: Dict[str, str] = field(default_factory=dict)
    Prerequisites: List[str] = field(default_factory=list)


# Catalog Manifest
@dataclass
class CatalogManifest():
    Products: List[ProductManifest]
    Portfolios: List[PortfolioManifest]
    Dependencies: List[DependencyManifest]