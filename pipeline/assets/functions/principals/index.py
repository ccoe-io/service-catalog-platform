from os import environ
import json
import jmespath
import traceback
from aws.connection import SpokeSession, client
from botocore.exceptions import ClientError
from logger import logger
from aws.codepipeline import put_job_failure, put_job_success, download_input_artifact


REGION = environ['REGION']
MODEL_FILENAME = environ['MODEL_FILENAME']
ACCOUNTS_XACC_ROLE_NAME = environ['ACCOUNTS_XACC_ROLE_NAME']

ssm_client = client('ssm')
code_pipeline = client('codepipeline')
sc_client = client('servicecatalog')

PORTFOLIOS_IDS = {}

def get_portfolio_id(portfolio_mid):
    if PORTFOLIOS_IDS.get(portfolio_mid):
        return PORTFOLIOS_IDS.get(portfolio_mid)
    portfolio_id = ssm_client.get_parameter(
        Name=f'/idp/stacks/portfolios/{portfolio_mid}')['Parameter']['Value']
    logger.debug('Portfolio_id: {}'.format(portfolio_id))
    PORTFOLIOS_IDS[portfolio_mid] = portfolio_id
    return portfolio_id


def get_accounts(model):
    parsed_accounts = jmespath.search(
        "portfolios.items[].accounts|[][]", model)
    logger.debug('parsed_accounts: {}'.format(parsed_accounts))
    if parsed_accounts: 
        accounts = list(set(parsed_accounts))
    else:
        accounts = []
    logger.debug('accounts: {}'.format(accounts))
    return accounts


def add_principals(account_id, model):
    spoke_session = SpokeSession(ACCOUNTS_XACC_ROLE_NAME, account_id, REGION)
    sc_spoke_client = spoke_session.client('servicecatalog')
    iam_spoke_client = spoke_session.client('iam')

    paginator = iam_spoke_client.get_paginator('list_roles')
    response_iterator = paginator.paginate()

    for response in response_iterator:
        for role in response['Roles']:
            logger.debug(f'Role: {role}')
            for portfolio in model['portfolios']['items']:
                portfolio_id = get_portfolio_id(portfolio['mid'])
                logger.debug(f'Portfolio Id: {portfolio_id}')
                for principal_selector in portfolio['principals']:
                    if principal_selector['SelectorType'] == 'RoleName':
                        for value in principal_selector['Values']:
                            logger.debug(f'Selector value: {value}')
                            if value in role['RoleName']: 
                                try:
                                    sc_spoke_client.associate_principal_with_portfolio(
                                        PortfolioId=portfolio_id,
                                        PrincipalARN=role['Arn'],
                                        PrincipalType='IAM'
                                    )
                                except ClientError as err:
                                    if err.response['Error']['Code'] == 'ResourceNotFoundException':
                                        pass


def handler(event, context) -> None:
    job_id = event['CodePipeline.job']['id']
    try:
        download_input_artifact(event)
        with open(f'/tmp/{MODEL_FILENAME}', 'r') as fh:
           model = json.load(fh)
        logger.debug('Model: {}'.format(json.dumps(model)))
        accounts = get_accounts(model)
        logger.debug(accounts)
        for account in accounts:
            add_principals(account, model)
        put_job_success(job_id, 'Accept shares successfuly')
    except Exception as err:
        logger.debug(traceback.format_exc())
        put_job_failure(job_id, 'failed with error: {}'.format(err))
