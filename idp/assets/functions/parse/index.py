# import sys
# import os
# sys.path.append(os.path.join(os.path.dirname(__file__)))

from os import environ, path
from typing import List
from dataclasses import asdict
import traceback
import json
from logger import logger
from utils import (
    find_local_files,
    create_yaml_file,
    create_json_file
)
from aws import codepipeline
from aws.ssm import accounts_state
from aws.dynamodb import versions_table
from manifest.manifest import (
    ProductManifest,
    PortfolioManifest,
    CatalogManifest,
    DependencyManifest
)
from model.catalog import Catalog

ACCOUNT_ID = environ['ACCOUNT_ID']
BASE_PATH = environ['LAMBDA_TASK_ROOT']
ACCOUNTS_XACC_ROLE_NAME = environ['ACCOUNTS_XACC_ROLE_NAME']
OUTPUT_ARTIFACT_INDEX_DEPS = environ['OUTPUT_ARTIFACT_INDEX_DEPS']
OUTPUT_ARTIFACT_INDEX_MODEL = environ['OUTPUT_ARTIFACT_INDEX_MODEL']
MODEL_FILENAME = environ['MODEL_FILENAME']

PRODUCTS_PATH = environ.get('PRODUCTS_PATH', 'products/')
PRODUCT_MANIFEST_FILENAME = 'manifest.yml'
PORTFOLIOS_PATH = environ.get('PORTFOLIOS_PATH', 'portfolios/')
PORTFOLIO_MANIFEST_FILENAME = 'manifest.yml'
DEPENDENCIES_PATH = environ.get('DEPENDENCIES_PATH', 'dependencies/')
DEPENDENCY_MANIFEST_FILENAME = 'manifest.yml'

# Manifests

def load_catalog_manifest() -> CatalogManifest:
    products_files = find_local_files(PRODUCTS_PATH, PRODUCT_MANIFEST_FILENAME)
    portfolios_files = find_local_files(PORTFOLIOS_PATH, PORTFOLIO_MANIFEST_FILENAME)
    dependencies_files = find_local_files(DEPENDENCIES_PATH, DEPENDENCY_MANIFEST_FILENAME)

    prodms = []
    for prodmf in products_files:
        prodmf = path.abspath(prodmf)
        logger.debug(f'Manifest path: {prodmf}')
        prodm = ProductManifest(prodmf)
        prodm.datafile.load()
        prodm.base_path = path.dirname(prodmf)
        prodms.append(prodm)
    portms = []
    for portmf in portfolios_files:
        portmf = path.abspath(portmf)
        logger.debug(f'Manifest path: {portmf}')
        portm = PortfolioManifest(portmf)
        portm.datafile.load()
        portm.base_path = path.dirname(portmf)
        portms.append(portm)
    dependms = []
    for dependmf in dependencies_files:
        dependmf = path.abspath(dependmf)
        logger.debug(f'Manifest path: {dependmf}')
        dependm = DependencyManifest(dependmf)
        dependm.datafile.load()
        dependm.base_path = path.dirname(dependmf)
        dependms.append(dependm)
    return CatalogManifest(Products=prodms, Portfolios=portms, Dependencies=dependms)

# Dependencies
def render_dependencies_parent_templates(catalog: Catalog) -> List[str]:
    resources = {}
    for product in catalog.products.items:
        active_ver = [ver for ver in product.versions.items if ver.active]
        logger.debug("active ver: {} \n launch_role: {} \n exists: {}".format(
            active_ver,
            product.artifact_launch_role,
            product.launch_role_exists
        ))
        if len(active_ver) > 0 and product.artifact_launch_role and not product.launch_role_exists:
            resource = product.render_nested_stack_launch_role_resource()
            for account_id in product.assoc_accounts+[ACCOUNT_ID]:
                if resources.get(account_id):
                    resources[account_id].update(resource)
                else:
                    resources[account_id] = resource
    for dependency in catalog.dependencies.items:
        resource = dependency.render_nested_stack_resource()
        for account_id in dependency.assoc_accounts:
            if resources.get(account_id):
                resources[account_id].update(resource)
            else:
                resources[account_id] = resource
    files = []
    for account_id, ress in resources.items():
        files.append(create_json_file({"Resources":ress}, file_name=f'{account_id}.json'))
    return files


def render_dependencies_buildspec(files: list) -> dict:
    deploy_accounts = []
    delete_accounts = accounts_state.get()
    builds = []
    for file_name in files:
        account_id = path.basename(file_name).split('.')[0]
        deploy_accounts.append(account_id)
        try:
            delete_accounts.remove(account_id)
        except ValueError:
            pass
        builds.append(
            {
                'identifier': f'{account_id}_deploy',
                'ignore-failure': False,
                'buildspec': "deploy.yml",
                'env': {
                    "variables": {
                        "role_arn": f'arn:aws:iam::{account_id}:role/{ACCOUNTS_XACC_ROLE_NAME}',
                        "template_file_name": path.basename(file_name),
                        "stack_name": f'SC-idp-dependencies'
                    }
                }
            }
        )
    accounts_state.save(deploy_accounts)
    for account_id in delete_accounts:
        builds.append(
            {
                'identifier': f'{account_id}_delete',
                'ignore-failure': False,
                'buildspec': "delete.yml",
                'env': {
                    "variables": {
                        "role_arn": f'arn:aws:iam::{account_id}:role/{ACCOUNTS_XACC_ROLE_NAME}',
                        "stack_name": f'SC-idp-dependencies'
                    }
                }
            }
        )
    if not builds:
        builds = [{
            'identifier': 'build55',
            'ignore-failure': False,
            'buildspec': "delete.yml",
            'env': {
                "variables": {
                    "action": "delete",
                    "role_arn": f'arn:aws:iam::{ACCOUNT_ID}:role/{ACCOUNTS_XACC_ROLE_NAME}',
                    "stack_name": 'SC-dummyrole'
                }
            }
        }]
    return {
        "version": 0.2,
        "batch": {
            "build-list": builds
        }
    }

# handler

def handler(event, context) -> None:
    logger.debug(json.dumps(event, sort_keys=True, indent=4, default=str))
    job_id = event['CodePipeline.job']['id']
    try:
        codepipeline.download_input_artifact(event)
        # build model from manifest
        catalog_manifests = load_catalog_manifest()
        logger.debug(json.dumps(asdict(catalog_manifests), sort_keys=True, indent=4, default=str))
        catalog_model = Catalog(catalog_manifests)
        logger.debug(json.dumps(asdict(catalog_model), sort_keys=True, indent=4, default=str))
        model_file_path = create_json_file(asdict(catalog_model), file_name=MODEL_FILENAME)
        codepipeline.upload_output_artifact(
            event,
            int(OUTPUT_ARTIFACT_INDEX_MODEL),
            model_file_path
        )
        # update the versions state according to manifests
        versions_table.save_versions([asdict(ver) for ver in catalog_model.versions])
        # create depedencies buildspec and publish as output artifcat
        dependencies_accounts_templates = render_dependencies_parent_templates(catalog_model)
        dependencies_buildspec = render_dependencies_buildspec(dependencies_accounts_templates)
        buildspec_file_path = create_yaml_file(dependencies_buildspec, file_name='buildspec.yml')
        codepipeline.upload_output_artifact(
            event,
            int(OUTPUT_ARTIFACT_INDEX_DEPS),
            buildspec_file_path,
            path.join(BASE_PATH, 'assets', 'session.sh'),
            path.join(BASE_PATH, 'assets', 'deploy.yml'),
            path.join(BASE_PATH, 'assets', 'delete.yml'),
            path.join(BASE_PATH, 'assets', 'deploy.sh'),
            *dependencies_accounts_templates
        )
        # send success result to the pipeline
        codepipeline.put_job_success(job_id, 'Parsed manifests successfuly')
    except Exception as err:
        logger.debug(traceback.format_exc())
        codepipeline.put_job_failure(job_id, 'failed with error: {}'.format(err))

# if __name__ == '__main__':
#     # export ACCOUNT_ID='xxxxxxxxx'
#     # export LAMBDA_TASK_ROOT='./'
#     # export ACCOUNTS_XACC_ROLE_NAME=xxac-test-role
#     # export CATALOG_TABLE_NAME=IdpStack-CatalogTableF8EA09BD-1I1OYWCXVCTZL
#     # export CATALOG_ARTIFACTS_BUCKET_REGION=eu-west-1
#     # export CATALOG_ARTIFACTS_BUCKET=XXXX-eu-west-1-idp-catalog
#     # export OUTPUT_ARTIFACT_INDEX_DEPS=0
#     # export OUTPUT_ARTIFACT_INDEX_MODEL=1
#     # export MODEL_FILENAME=model.json
#     # export PRODUCTS_PATH='/Users/dronen/workspace/solutions/idp-sc-catalog-test001/products'
#     # export PORTFOLIOS_PATH='/Users/dronen/workspace/solutions/idp-sc-catalog-test001/portfolios'
#     # export DEPENDENCIES_PATH='/Users/dronen/workspace/solutions/idp-sc-catalog-test001/dependencies'
#     import json
#     catalog_manifests = load_catalog_manifest()
#     print(json.dumps(asdict(catalog_manifests), sort_keys=True, indent=4, default=str))
#     catalog_model = Catalog(catalog_manifests)
#     print(json.dumps(asdict(catalog_model), sort_keys=True, indent=4, default=str))
#     # versions_table.save_versions([asdict(ver) for ver in catalog_model.versions])
#     dependencies_buildspec = render_dependencies_buildspec(catalog_model)
#     print(json.dumps(dependencies_buildspec, sort_keys=True, indent=4, default=str))
#     print(create_yaml_file(dependencies_buildspec))
