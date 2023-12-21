from aws_cdk import (
    Stack,
    aws_servicecatalog as servicecatalog
)
from constructs import Construct
import boto3
from botocore.exceptions import ClientError
from .logger import logger
from . import utils

SSM_PARAMETER_NAME_PRODUCTS = '/core/service-catalog/products/{}'
SSM_PARAMETER_NAME_PORTFOLIOS = '/core/service-catalog/portfolios/{}'
SSM_PARAMETER_NAME_TAGOPTIONS = '/core/service-catalog/tagoptions/{}'

ssm_client = boto3.session.Session().client('ssm')


class AssocStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, model: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        mproducts = utils.from_model(model, 'products.items[]')
        for mproduct in mproducts:
            try:
                product_id = ssm_client.get_parameter(
                    Name=SSM_PARAMETER_NAME_PRODUCTS.format(mproduct['mid']))['Parameter']['Value']
                self.create_tag_assoc(product_id, mproduct['assoc_tag_options'])
            except ClientError as err:
                if not err.response['Error']['Code'] == 'ParameterNotFound':
                    raise(err)
        mportfolios = utils.from_model(model, 'portfolios.items[]')
        for mportfolio in mportfolios:
            try:
                portfolio_id = ssm_client.get_parameter(
                    Name=SSM_PARAMETER_NAME_PORTFOLIOS.format(mportfolio['mid']))['Parameter']['Value']
                self.create_tag_assoc(portfolio_id, mportfolio['assoc_tag_options'])
            except ClientError as err:
                if not err.response['Error']['Code'] == 'ParameterNotFound':
                    raise(err)

        for mportfolio in mportfolios:
            for product_mid in mportfolio['assoc_products']:
                mproduct = utils.from_model(model, f"products.items[?mid=='{product_mid}']|[0]")
                if mproduct:
                    self.associate_product_to_portfolio(mportfolio, mproduct)

    def create_tag_assoc(self, resource_id: str, tag_options_mids: list) -> None:
        for tag_option_mid in tag_options_mids:
            logger.debug("CDK render Assoc: {} tag: {}".format(resource_id, tag_option_mid))
            try:
                tag_option_id = ssm_client.get_parameter(
                    Name=SSM_PARAMETER_NAME_TAGOPTIONS.format(tag_option_mid))['Parameter']['Value']
                servicecatalog.CfnTagOptionAssociation(self, f"{resource_id}{tag_option_mid}",
                    resource_id=resource_id,
                    tag_option_id=tag_option_id
                )
            except ClientError as err:
                if not err.response['Error']['Code'] == 'ParameterNotFound':
                    raise(err)

    def associate_product_to_portfolio(self, mportfolio, mproduct):
        try:
            portfolio_id = ssm_client.get_parameter(
                Name=SSM_PARAMETER_NAME_PORTFOLIOS.format(mportfolio['mid']))['Parameter']['Value']
            product_id = ssm_client.get_parameter(
                Name=SSM_PARAMETER_NAME_PRODUCTS.format(mproduct['mid']))['Parameter']['Value']
            launch_role_name = mproduct['launch_role_name']

            ppassoc = servicecatalog.CfnPortfolioProductAssociation(
                self, "Assoc"+portfolio_id+product_id,
                portfolio_id=portfolio_id,
                product_id=product_id)

            launch_role_constraint = servicecatalog.CfnLaunchRoleConstraint(
                self, "LaunchRoleConstraint"+portfolio_id+product_id,
                portfolio_id=portfolio_id,
                product_id=product_id,
                local_role_name=launch_role_name
            )
            launch_role_constraint.add_depends_on(ppassoc)
        except ClientError as err:
                if not err.response['Error']['Code'] == 'ParameterNotFound':
                    raise(err)
