from constructs import Construct
from aws_cdk import (
    Stage
)
from idp.idp_stack import IdpStack


class ApplicationPipelineStage(Stage):

    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        service = IdpStack(self, 'service-catalog-catalog')
