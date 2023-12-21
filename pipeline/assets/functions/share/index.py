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


def get_portfolios():
    portfolios_ssm = ssm_client.get_parameters_by_path(Path='/idp/stacks/portfolios')
    portfolios_ids = jmespath.search("Parameters[].Value", portfolios_ssm)
    logger.debug('Portfolios: {}'.format(portfolios_ids))
    return portfolios_ids


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


def accept_share(account_id):
    portfolios = get_portfolios()
    spoke_session = SpokeSession(ACCOUNTS_XACC_ROLE_NAME, account_id, REGION)
    sc_spoke_client = spoke_session.client('servicecatalog')
    for portfolio in portfolios:
        try:
            logger.debug(f'Trying to accept share {portfolio} in account {account_id}')
            sc_spoke_client.accept_portfolio_share(
                PortfolioId=portfolio,
                PortfolioShareType='IMPORTED'
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
            accept_share(account)
        put_job_success(job_id, 'Accept shares successfuly')
    except Exception as err:
        logger.debug(traceback.format_exc())
        put_job_failure(job_id, 'failed with error: {}'.format(err))
