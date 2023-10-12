import sys
from os import environ
import logging
import json
import jmespath
import traceback
import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stdout_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stdout_handler)

PORTFOLIOS_SSM_PARAMETER = environ['PORTFOLIOS_SSM_PARAMETER']
ACCOUNTS_XACC_ROLE_NAME = environ['ACCOUNTS_XACC_ROLE_NAME']

session = boto3.session.Session()
region = session.region_name
sts_client = session.client('sts')
ssm_client = session.client('ssm')
code_pipeline = session.client('codepipeline')
sc_client = session.client('servicecatalog')


def get_portfolios():
    portfolios = sc_client.list_portfolios()
    portfolios_ids = jmespath.search(
        "PortfolioDetails[].{Id:Id, Name:DisplayName}", portfolios)
    return portfolios_ids


def get_portfolios_details() -> list:
    param = ssm_client.get_parameter(Name=PORTFOLIOS_SSM_PARAMETER)
    portfolios = param['Parameter']['Value']
    return json.loads(portfolios)


def get_accounts():
    param = ssm_client.get_parameter(Name=PORTFOLIOS_SSM_PARAMETER)
    portfolios = param['Parameter']['Value']
    accounts = list(set(jmespath.search(
        "[].SharesAccounts|[][]", json.loads(portfolios))))
    return accounts


def get_portfolios_id_rolenames():
    portfolios_ids = get_portfolios()
    portfolios = []
    for portfolio in get_portfolios_details():
        principals = portfolio['Principals']
        name = portfolio['Name']
        portfolio_id = jmespath.search(
            f"[?Name=='{name}'].Id|[0]", portfolios_ids)
        roles_names = principals.get('Name')
        portfolios.append({
            'roles-names': roles_names,
            'id': portfolio_id
        })
    return portfolios


def add_principals(account_id):
    portfolios = get_portfolios_id_rolenames()
    spoke_session = SpokeSession(ACCOUNTS_XACC_ROLE_NAME, account_id, region)
    sc_spoke_client = spoke_session.client('servicecatalog')
    iam_spoke_client = spoke_session.client('iam')

    paginator = iam_spoke_client.get_paginator('list_roles')
    response_iterator = paginator.paginate()
    roles = []
    for response in response_iterator:
        roles += response['Roles']

    for portfolio in portfolios:
        roles_list = []
        roles_names = portfolio['roles-names']
        portfolio_id = portfolio['id']
        for rname in roles_names:
            roles_list += jmespath.search(
                f"[?contains(RoleName, '{rname}')].Arn", roles)
        for principal in roles_list:
            try:
                sc_spoke_client.associate_principal_with_portfolio(
                    PortfolioId=portfolio_id,
                    PrincipalARN=principal,
                    PrincipalType='IAM'
                )
            except ClientError as err:
                if err.response['Error']['Code'] == 'ResourceNotFoundException':
                    pass


def put_job_success(job, message):
    logger.info('Putting job success')
    logger.info(message)
    code_pipeline.put_job_success_result(jobId=job)


def put_job_failure(job, message):
    logger.info('Putting job failure')
    logger.info(message)
    code_pipeline.put_job_failure_result(
        jobId=job, failureDetails={'message': message, 'type': 'JobFailed'})


def handler(event, context) -> None:
    job_id = event['CodePipeline.job']['id']
    try:
        for account in get_accounts():
            add_principals(account)
        put_job_success(job_id, 'Accept shares successfuly')
    except Exception as err:
        logger.debug(traceback.format_exc())
        put_job_failure(job_id, 'failed with error: {}'.format(err))


class SpokeSession(boto3.session.Session):

    def __init__(self, role_name, account_id, region_name):
        role_arn = 'arn:aws:iam::{account_id}:role/{role_name}'.format(
            account_id=account_id,
            role_name=role_name
        )
        response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName=str(account_id)
        )
        super().__init__(
            region_name=region_name,
            aws_access_key_id=response['Credentials']['AccessKeyId'],
            aws_secret_access_key=response['Credentials']['SecretAccessKey'],
            aws_session_token=response['Credentials']['SessionToken']
        )
