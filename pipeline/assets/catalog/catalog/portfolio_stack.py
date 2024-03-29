from aws_cdk import (
    Stack,
    Duration,
    CustomResource,
    aws_servicecatalog as servicecatalog,
    aws_ssm as ssm,
    aws_lambda as lambda_,
    aws_iam as iam
)
from constructs import Construct
from .logger import logger
from . import utils

SSM_PARAMETER_NAME_PORTFOLIOS = '/core/service-catalog/portfolios/{}'


class PortfolioStack(Stack):

    def __init__(
        self, scope: Construct, construct_id: str, model: dict, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        managed_policy_lambda_exec = iam.ManagedPolicy.from_managed_policy_arn(
            self,
            'policylambdaexec',
            'arn:aws:iam::aws:policy/AWSLambdaExecute')
        provider_role = iam.Role(
            self, "ProviderLambdaExecRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[managed_policy_lambda_exec]
        )

        self.share_portfolio_function = lambda_.Function(
            self, "SharePortfolio",
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset('catalog/cr'),
            handler="index.handler",
            role=provider_role,
            timeout=Duration.seconds(120),
            memory_size=1024,
            description="Provider for share portfolio custom resource"
        )
        self.share_portfolio_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "servicecatalog:CreatePortfolioShare",
                    "servicecatalog:DeletePortfolioShare",
                    "servicecatalog:UpdatePortfolioShare",
                    "organizations:List*"
                ],
                resources=["*"]
            )
        )

        portfolios = utils.from_model(model, 'portfolios.items[]')
        for portfolio in portfolios:
            self.create_portfolio(portfolio)

    def create_portfolio(self, portfolio):
        logger.debug("CDK render Portfolio: {}".format(portfolio['mid']))
        portfolio_res = servicecatalog.Portfolio(
            self, "Portfolio"+portfolio['mid'],
            display_name=portfolio['Name'],
            provider_name=portfolio['ProviderName'],
            description=portfolio['Description'],
            message_language=servicecatalog.MessageLanguage.EN,
        )

        shares = portfolio['shares']
        for account_id in shares.get('AccountsIds', []):
            self.custom_resource(account_id, "ACCOUNT", portfolio['mid'], portfolio_res)
        for ou_id in shares.get('OrgUnitsIds', []):
            self.custom_resource(ou_id, "ORGANIZATIONAL_UNIT", portfolio['mid'], portfolio_res)
        for org_id in shares.get('OrgIds', []):
            self.custom_resource(org_id, "ORGANIZATION", portfolio['mid'], portfolio_res)
    
        for principal in portfolio['principals']:
            if principal['SelectorType'] != 'RoleName':
                logger.error(
                    f"Unsupported pricipal selector type: \
                    {principal['SelectorType']}")
            else:
                for i, v in enumerate(principal['Values']):
                    servicecatalog.CfnPortfolioPrincipalAssociation(
                        self,
                        "ppa-"+portfolio['mid']+str(i),
                        portfolio_id=portfolio_res.portfolio_id,
                        principal_arn=f"arn:aws:iam:::role/{v}",
                        principal_type="IAM_PATTERN"
                    )

        ssm.StringParameter(
            self, "portssmArn"+portfolio['mid'],
            data_type=ssm.ParameterDataType.TEXT,
            string_value=portfolio_res.portfolio_id,
            parameter_name=SSM_PARAMETER_NAME_PORTFOLIOS.format(portfolio["mid"]), 
            simple_name=False
        )

    def custom_resource(self, object_id, node_type, portfolio_id, portfolio_res):
        CustomResource(
            self, "share-"+object_id+portfolio_id,
            service_token=self.share_portfolio_function.function_arn,
            properties={
                "PortfolioId": portfolio_res.portfolio_id,
                "NodeType": node_type,
                "NodeId": object_id
            }
        )
        # portfolio_res.share_with_account(
        #     account_id, share_tag_options=True)

