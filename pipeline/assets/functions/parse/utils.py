from os import path, walk
from zipfile import ZipFile
import json
import yaml
import tempfile
import hashlib
import urllib3
from glob import glob
from logger import logger


def zipdir(path: str, ziph: ZipFile) -> None:
    # ziph is zipfile handle
    for root, dirs, files in walk(path):
        for file in files:
            ziph.write(
                path.join(root, file),
                path.relpath(
                    path.join(root, file),
                    path.join(path, '..')
                )
            )


def calculate_file_md5(file_path: str) -> str:
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as fh:
        for byte_block in iter(lambda: fh.read(4096), b""):
            md5_hash.update(byte_block)
    return md5_hash.hexdigest()


def render_role_template(role_name: str, policies_file_path: str) -> str:
    role = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "RootRole": {
                "Type": "AWS::IAM::Role",
                "Properties": {
                    "RoleName": {
                        "Fn::Sub": [
                            "${RoleName}",
                            {
                                "RoleName": role_name
                            }
                        ]
                    },
                    "AssumeRolePolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {
                                    "Service": [
                                        "servicecatalog.amazonaws.com"
                                    ]
                                },
                                "Action": ["sts:AssumeRole"]
                            }
                        ]
                    },
                    "Path": "/"
                }
            }
        }
    }

    with open(policies_file_path, 'r') as fh:
        policies = json.load(fh)
    managed_policies = policies.get('ManagedPolicyArns')
    inline_policies = policies.get('Policies')
    if managed_policies:
        role['Resources']['RootRole']['Properties']['ManagedPolicyArns'] = managed_policies
    if inline_policies:
        role['Resources']['RootRole']['Properties']['Policies'] = inline_policies

    tmp_file = './launch-role.json'
    with open(tmp_file, 'w+') as fh:
        json.dump(role, fh)
    return path.abspath(tmp_file)


def find_local_files(start_path, file_name) -> list:
    files = []
    for folder in glob(path.join(start_path,'*'), recursive=True):
        logger.info(folder+'/'+file_name)
        try:
            file_path = glob(folder+'/'+file_name)[0]
            files.append(file_path)
        except IndexError:
            logger.warning(f'File path {folder} does not include manifest')
            continue
    return files


def s3url_parse(url):
    parsed = urllib3.util.parse_url(url)
    return (parsed.host.split('.')[0], parsed.path.split('/')[-1], "/".join(parsed.path.split('/')[0:-1]))


def create_yaml_file(data: dict, file_name: str=None) -> str:
    if not file_name:
        file_name = path.basename(tempfile.mktemp())
    with open(file_name, 'w+') as fh:
        yaml.dump(data, fh)
    return path.abspath(file_name)


def create_json_file(data: dict, file_name: str=None) -> str:
    if not file_name:
        file_name = path.basename(tempfile.mktemp())
    with open(file_name, 'w+') as fh:
        json.dump(data, fh, default=str)
    return path.abspath(file_name)


def nested_stack_resource(
    logical_id: str, template_url: str,
    parameters: dict = None, depends_on: list = None,
    comment: str = None
) -> dict:

    if not comment:
        comment = logical_id
    resource = {
        logical_id:
        {
            "Type": "AWS::CloudFormation::Stack",
            "Properties": {
                "Tags": [{"Key": "core-sc-platform", "Value": f"{comment}"}],
                "TemplateURL": template_url,
                "TimeoutInMinutes": 35
            }
        }
    }
    if parameters:
        resource[logical_id]['Properties']['Parameters'] = parameters
    if depends_on:
        resource[logical_id]['DependsOn'] = depends_on
    return resource
