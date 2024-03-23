import os
import logging
from time import sleep
import boto3
from botocore.exceptions import ClientError
from crhelper import CfnResource

logger = logging.getLogger(__name__)
LOG_LEVEL = os.environ.get("LOG_LEVEL", logging.DEBUG)
logger.setLevel(LOG_LEVEL)

helper = CfnResource(
    json_logging=False,
    log_level='DEBUG',
    boto_level='CRITICAL',
    sleep_on_delete=120,
    ssl_verify=None
)

try:
    # Init code goes here
    session = boto3.session.Session()
    client = session.client('servicecatalog')
except Exception as e:
    helper.init_failure(e)


@helper.create
def create(event, context):
    logger.info("Got Create")
    portfolio_id = event['ResourceProperties']['PortfolioId']
    node_id = event['ResourceProperties']['NodeId']
    node_type = event['ResourceProperties']['NodeType']

    try:
        share(node_id, node_type, portfolio_id)
    except ClientError as err:
        if err.response['Error']['Code'] == 'InvalidStateException':
            sleep(40)
            share(node_id, node_type, portfolio_id)

    physical_id = "share-" + portfolio_id + node_id
    return physical_id


def share(node_id, node_type, portfolio_id):
    client.create_portfolio_share(
        PortfolioId=portfolio_id,
        OrganizationNode={
            'Type': node_type,
            'Value': node_id
        },
        ShareTagOptions=True,
        SharePrincipals=True
    )


@helper.update
def update(event, context):
    logger.info("Got Update")
    physical_id = event['PhysicalResourceId']

    portfolio_id = event['ResourceProperties']['PortfolioId']
    node_id = event['ResourceProperties']['NodeId']
    node_type = event['ResourceProperties']['NodeType']

    try:
        update_share(node_id, node_type, portfolio_id)
    except ClientError as err:
        if err.response['Error']['Code'] == 'InvalidStateException':
            sleep(40)
            update_share(node_id, node_type, portfolio_id)

    physical_id = "share-" + portfolio_id + node_id
    return physical_id


def update_share(node_id, node_type, portfolio_id):
    client.update_portfolio_share(
        PortfolioId=portfolio_id,
        OrganizationNode={
            'Type': node_type,
            'Value': node_id
        },
        ShareTagOptions=True,
        SharePrincipals=True
    )


@helper.delete
def delete(event, context):
    logger.info("Got Delete")

    portfolio_id = event['ResourceProperties']['PortfolioId']
    node_id = event['ResourceProperties']['NodeId']
    node_type = event['ResourceProperties']['NodeType']

    client.delete_portfolio_share(
        PortfolioId=portfolio_id,
        OrganizationNode={
            'Type': node_type,
            'Value': node_id
        }
    )


def handler(event, context):
    helper(event, context)
