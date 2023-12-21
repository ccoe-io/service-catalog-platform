from aws_cdk import (
    Stack,
    aws_servicecatalog as servicecatalog,
    aws_ssm as ssm
)
from constructs import Construct
from .logger import logger
from . import utils

SSM_PARAMETER_NAME_PRODUCTS = '/core/service-catalog/products/{}'
SSM_PARAMETER_NAME_PORTFOLIOS = '/core/service-catalog/portfolios/{}'
SSM_PARAMETER_NAME_TAGOPTIONS = '/core/service-catalog/tagoptions/{}'


class TagOptionStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, model: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        tag_options = utils.from_model(model, 'tag_options.items[]')

        for tag_option in tag_options:
            self.create_tag_option(tag_option)

    def create_tag_option(self, tag_option: dict):
        tag_option_res = servicecatalog.CfnTagOption(
            self, "TagOptions"+tag_option['mid'],
            key=tag_option["key"],
            value=tag_option["value"]
        )

        ssm.StringParameter(
            self, "ssmTagOptions"+tag_option['mid'],
            data_type=ssm.ParameterDataType.TEXT,
            string_value=tag_option_res.ref,
            parameter_name=SSM_PARAMETER_NAME_TAGOPTIONS.format(
                tag_option["mid"]),
            simple_name=False
        )
