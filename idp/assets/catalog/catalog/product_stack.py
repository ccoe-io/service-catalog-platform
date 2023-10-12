from aws_cdk import (
    Stack,
    aws_servicecatalog as servicecatalog,
    aws_ssm as ssm
)
from constructs import Construct
from .logger import logger
from . import utils


class ProductStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, model: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        products = utils.from_model(model, 'products.items[]')
        for product in products:
            self.create_product(product)

    def create_product(self, product):
        logger.debug("CDK render Product: {}".format(product['mid']))
        product_res = servicecatalog.CloudFormationProduct(
            self, "Product"+product['mid'],
            product_name=product['Name'],
            owner=product['Owner'],
            description=product['Description'],
            distributor=product['Distributor'],
            support_description=product['SupportDescription'],
            support_email=product['SupportEmail'],
            support_url=product['SupportUrl'],
            product_versions=[
                servicecatalog.CloudFormationProductVersion(
                    product_version_name=version['label'],
                    cloud_formation_template=servicecatalog.CloudFormationTemplate.from_url(
                        version['template_url']),
                    description=version['description']
                ) for version in product['versions']['items'] if version['active']
            ]
        )
        ssm.StringParameter(
            self, "prodssmArn"+product['mid'],
            data_type=ssm.ParameterDataType.TEXT,
            string_value=product_res.product_id,
            parameter_name=f'/idp/stacks/products/{product["mid"]}',
            simple_name=False
        )
