#!/usr/bin/env python3
import aws_cdk as cdk
from aws_cdk import Tags
import os
from catalog import utils
from catalog.portfolio_stack import PortfolioStack
from catalog.product_stack import ProductStack
from catalog.tagoption_stack import TagOptionStack
from catalog.assoc_stack import AssocStack

from tags import tags

app = cdk.App()
# CatalogStack(app, "CatalogStack",
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
#    )

model = utils.get_model()

assoc_stack = AssocStack(
    app, "core-service-catalog-associations", model,
    env=cdk.Environment(
        account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
        region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"])
    )
)

tagoption_stack = TagOptionStack(
    app, "core-service-catalog-tagOptions", model,
    env=cdk.Environment(
        account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
        region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"])
    )
)

product_stack = ProductStack(
    app, "core-service-catalog-products", model,
    env=cdk.Environment(
        account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
        region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"])
    )
)

portfolio_stack = PortfolioStack(
    app, "core-service-catalog-portfolios", model,
    env=cdk.Environment(
        account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
        region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"])
    )
)

for k, v in tags.items():
    Tags.of(assoc_stack).add(k, v)
    Tags.of(tagoption_stack).add(k, v)
    Tags.of(product_stack).add(k, v)
    Tags.of(portfolio_stack).add(k, v)

app.synth()
