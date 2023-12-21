import os
import logging
import boto3
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

    client.create_portfolio_share(
        PortfolioId=portfolio_id,
        OrganizationNode={
            'Type': node_type,
            'Value': node_id
        },
        ShareTagOptions=True,
        SharePrincipals=True
    )
    physical_id = "share-" + portfolio_id + node_id
    return physical_id


@helper.update
def update(event, context):
    logger.info("Got Update")
    physical_id = event['PhysicalResourceId']

    portfolio_id = event['ResourceProperties']['PortfolioId']
    node_id = event['ResourceProperties']['NodeId']
    node_type = event['ResourceProperties']['NodeType']

    client.update_portfolio_share(
        PortfolioId=portfolio_id,
        OrganizationNode={
            'Type': node_type,
            'Value': node_id
        },
        ShareTagOptions=True,
        SharePrincipals=True
    )
    physical_id = "share-" + portfolio_id + node_id
    return physical_id


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
