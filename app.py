#!/usr/bin/env python3
from aws_cdk import (
    App,
    Tags
)

from pipeline.pipeline_stack import PipelineStack
from tags import tags

app = App()
pipeline_stack = PipelineStack(
    app, "core-service-catalog-platfrom",
    tags=tags,
    # If you don't specify 'env', this stack will be environment-agnostic.
    # Account/Region-dependent features and context lookups will not work,
    # but a single synthesized template can be deployed anywhere.

    # Uncomment the next line to specialize this stack for the AWS Account
    # and Region that are implied by the current CLI configuration.

    #env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),

    # Uncomment the next line if you know exactly what Account and Region you
    # want to deploy the stack to. */

    #env=cdk.Environment(account='123456789012', region='us-east-1'),

    # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
    )

for k, v in tags.items():
    Tags.of(pipeline_stack).add(k, v)

app.synth()
