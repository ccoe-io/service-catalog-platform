import boto3
from constructs import Construct
from aws_cdk import (
    Stack,
    Aws,
    Environment,
    pipelines as pipelines,
    aws_s3 as s3,
    aws_iam as iam,
    aws_ssm as ssm
)
from idp.app_stage_deploy import ApplicationPipelineStage

ssm_client = boto3.client('ssm')


class PipelineStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        target_account = self.account
        target_region = self.region
        deployment_target = self.node.try_get_context("DEPLOYMENT_TARGET")
        if deployment_target:
            target_account = deployment_target['account_id']
            target_region = deployment_target['region']

        catalog_source = self.node.try_get_context("CATALOG_SOURCE")
        iparam_catalog_connection_arn = ssm.StringParameter.from_string_parameter_name(
            self, "CataConnArniParameter",
            catalog_source['git']['connection_arn_ssm_parameter']
        )
        source = self.node.try_get_context("SOURCE")
        source_repo = source['git']['repo']
        source_branch = source['git']['branch']
        # source_connection_arn = source['git']['connection_arn']
        source_connection_arn = ssm_client.get_parameter(
            Name=source['git']['connection_arn_ssm_parameter']
        )['Parameter']['Value']

        iparam_org_id = ssm.StringParameter.from_string_parameter_name(
            self, "OrgIdiParameter",
            self.node.try_get_context("SSM_PARAM_NAME_ORG_ID")
        )

        iparam_connection_arn = ssm.StringParameter.from_string_parameter_name(
            self, "ConnArniParameter",
            source['git']['connection_arn_ssm_parameter']
        )

        pipeline = pipelines.CodePipeline(
            self,
            "Pipeline",
            synth=pipelines.ShellStep(
                "Synth",
                input=pipelines.CodePipelineSource.connection(
                    source_repo, source_branch,
                    connection_arn=source_connection_arn
                ),
                commands=[
                    "npm install -g aws-cdk",  # Installs the cdk cli on Codebuild
                    "pip install -r requirements.txt",  # Instructs Codebuild to install required packages
                    "cdk synth",
                ]
            ),
            cross_account_keys=True,
        )

        deploy = ApplicationPipelineStage(
            self, "Deploy",
            env=Environment(account=target_account, region=target_region))

        pipeline.add_stage(deploy)

        pipeline.build_pipeline()
        irole = pipeline.pipeline.stage("Build").actions[0].action_properties.resource.role
        iparam_org_id.grant_read(irole)
        iparam_connection_arn.grant_read(irole)
        iparam_catalog_connection_arn.grant_read(irole)
