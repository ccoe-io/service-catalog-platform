import boto3
from os import path
from aws_cdk import (
    Duration,
    Stack,
    Aws,
    aws_iam as iam,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    # aws_codecommit as codecommit,
    aws_codebuild as codebuild,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_ssm as ssm,
    aws_lambda as lambda_,
    aws_s3_assets as s3_assets
)
from aws_cdk.lambda_layer_awscli import AwsCliLayer
from constructs import Construct

ssm_client = boto3.client('ssm')


class IdpStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        org_id = ssm_client.get_parameter(
            Name=self.node.try_get_context("SSM_PARAM_NAME_ORG_ID")
        )['Parameter']['Value']

        source = self.node.try_get_context("CATALOG_SOURCE")
        # source_bucket = source['s3']['bucket_name']
        # source_key = source['s3']['bucket_key']
        source_org = source['git']['repo'].split('/')[0]
        source_list = source['git']['repo'].split('/')
        source_list.pop(0)
        source_repo = path.join(*source_list)
        source_branch = source['git']['branch']
        # source_connection_arn = source['git']['connection_arn']
        source_connection_arn = ssm_client.get_parameter(
            Name=source['git']['connection_arn_ssm_parameter']
        )['Parameter']['Value']

        spoke_xacc_role = self.node.try_get_context("SPOKE_XACC_ROLE")

        catalog_cdk_app = s3_assets.Asset(
            self, "CatalogCDKApp",
            path="idp/assets/catalog"
        )

        catalog_table = dynamodb.Table(
            self, "CatalogTable",
            partition_key=dynamodb.Attribute(
                name="product_id", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(
                name="label", type=dynamodb.AttributeType.STRING)
        )

        accounts_ssm_param_store = ssm.StringParameter(
            self,
            'accountsssmparameterstore',
            string_value="[]",
            parameter_name='/idp/accounts/state'
        )

        catalog_artifacts_bucket = s3.Bucket(
            self, "CatalogArtifactsBucket",
            versioned=True,
        )
        # TODO : allow read to org, write to pipeline only
        catalog_artifacts_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:*"],
                resources=[
                    catalog_artifacts_bucket.bucket_arn,
                    catalog_artifacts_bucket.arn_for_objects("*")
                ],
                principals=[iam.AnyPrincipal()],
                conditions={
                    "StringEquals": {
                        "aws:PrincipalOrgID": org_id
                    }
                }
            )
        )

        # TODO should remove the usage of Admin
        managed_admin_policy = iam.ManagedPolicy.from_managed_policy_arn(
            self,
            'policyadmin',
            'arn:aws:iam::aws:policy/AdministratorAccess')

        # repo = codecommit.Repository(
        #     self, "idp",
        #     repository_name="catalog"
        # )

        # -------------- Pipeline
        pipeline = codepipeline.Pipeline(self, "sc-platform")

        pipeline.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "codestar-connections:UseConnection",
                    "codestar-connections:GetConnection",
                    "codestar-connections:ListConnections",
                    "codestar-connections:TagResource",
                    "codestar-connections:ListTagsForResource",
                    "codestar-connections:UntagResource"
                ],
                resources=[source_connection_arn]
            )
        )

        # -------------- Source
        # TODO Parameterize source (s3bucket, github, bitbucket, codecommit)
        source_output = codepipeline.Artifact()

        # source_action = codepipeline_actions.CodeCommitSourceAction(
        #     action_name="CodeCommit",
        #     repository=repo,
        #     output=source_output,
        #     branch='main'
        # )

        # source_action = codepipeline_actions.GitHubSourceAction(
        #     action_name="Github_Source",
        #     output=source_output,
        #     owner="ccoe-io",
        #     repo="idp-sc-catalog",
        #     branch='main',
        #     oauth_token=SecretValue.secrets_manager("ccoe-io-github-token")
        # )
        # source_ibucket = s3.Bucket.from_bucket_name(
        #     self, "SourceBucket", source_bucket)
        # source_ibucket.grant_read(pipeline.role)

        source_action = codepipeline_actions.CodeStarConnectionsSourceAction(
            action_name="GitSource",
            owner=source_org,
            connection_arn=source_connection_arn,
            repo=source_repo,
            branch=source_branch,
            output=source_output,
            trigger_on_push=True
        )

        pipeline.add_stage(
            stage_name="Source",
            actions=[source_action]
        )

        # TODO least privileges
        buildprojectrole = iam.Role(
            self, "BuildProjectRole",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            managed_policies=[managed_admin_policy]
        )

        catalog_cdk_app.grant_read(buildprojectrole)

        # -------------- Scan artifacts
        # TODO add scanning for CFN
        scan_buildspec = {
            "version": 0.2,
            "phases": {
                "install": {
                    "runtime-versions": {
                        "nodejs": "latest"
                    }
                },
                "build": {
                    "commands": [
                        "echo 'run cfn-lint'"
                    ]
                }
            }
        }
        scan_build_project = codebuild.PipelineProject(
            self, "ScanArtifacts",
            build_spec=codebuild.BuildSpec.from_object(scan_buildspec),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0),
            role=buildprojectrole
        )
        scan_action = codepipeline_actions.CodeBuildAction(
            project=scan_build_project,
            action_name="scan",
            input=source_output,
            run_order=1
        )

        # -------------- Parse

        pylib_layer = lambda_.LayerVersion(
            self, "LambdaLayer",
            code=lambda_.Code.from_asset('idp/assets/functions/pylib'),
            description='Includes python packages required by IDP functions \
            (pyyaml, datafiles)',
            compatible_architectures=[
                lambda_.Architecture.X86_64, lambda_.Architecture.ARM_64]
        )
        # TODO least privilege
        parselambdarole = iam.Role(
            self, "ParseLambdaExecRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[managed_admin_policy]
        )

        model_filename = 'model.json'
        parse_lambda = lambda_.Function(
            self, 'ParseLambda',
            runtime=lambda_.Runtime.PYTHON_3_9,
            code=lambda_.Code.from_asset('idp/assets/functions/parse'),
            handler="index.handler",
            role=parselambdarole,
            timeout=Duration.seconds(120),
            memory_size=1024,
            environment={
                "CATALOG_ARTIFACTS_BUCKET": catalog_artifacts_bucket.bucket_name,
                "CATALOG_ARTIFACTS_BUCKET_REGION": Aws.REGION,
                "CATALOG_TABLE_NAME": catalog_table.table_name,
                "ACCOUNTS_SSM_PARAMETER_NAME": accounts_ssm_param_store.parameter_name,
                "ACCOUNTS_XACC_ROLE_NAME": spoke_xacc_role,
                "ACCOUNT_ID": Aws.ACCOUNT_ID,
                "OUTPUT_ARTIFACT_INDEX_DEPS": '0',
                "OUTPUT_ARTIFACT_INDEX_MODEL": '1',
                "MODEL_FILENAME": model_filename
            },
            layers=[pylib_layer]
        )
        parse_lambda.add_layers(AwsCliLayer(self, "AwsCliLayer"))

        parse_output_dependencies = codepipeline.Artifact()
        parse_output_model = codepipeline.Artifact()
        parse_action = codepipeline_actions.LambdaInvokeAction(
            action_name="parse",
            inputs=[source_output],
            lambda_=parse_lambda,
            run_order=2,
            outputs=[parse_output_dependencies, parse_output_model]
        )

        pipeline.add_stage(
            stage_name="HandleProductsArtifacts",
            actions=[scan_action, parse_action]
        )

        # ---------- Distribute dependencies
        dependencies_build_project = codebuild.PipelineProject(
            self, "DeployDependencies",
            build_spec=codebuild.BuildSpec.from_source_filename(
                "buildspec.yml"),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0),
            role=buildprojectrole
        )
        dependencies_action = codepipeline_actions.CodeBuildAction(
            execute_batch_build=True,
            project=dependencies_build_project,
            action_name="deploy",
            input=parse_output_dependencies,
            run_order=1
        )
        pipeline.add_stage(
            stage_name="DeployDependencies",
            actions=[dependencies_action]
        )

        # ----------  catalog cdk app
        catalog_buildspec = {
            "version": 0.2,
            "phases": {
                "install": {
                    "runtime-versions": {
                        "nodejs": "latest"
                    }
                },
                "build": {
                    "commands": [
                        "aws s3 cp $CATALOG_CDK_APP_S3URL ./catalog.zip",
                        "mkdir catalog",
                        "unzip catalog.zip",
                        "n 16",
                        "npm install -g aws-cdk",
                        "python -m pip install -r requirements.txt",
                        "ls -la",
                        "pwd",
                        f"cp {model_filename} catalog/{model_filename}",
                        f"cdk bootstrap aws://{Aws.ACCOUNT_ID}/{Aws.REGION}",
                        f"export CDK_DEPLOY_ACCOUNT={Aws.ACCOUNT_ID}",
                        f"export CDK_DEPLOY_REGION={Aws.REGION}",
                        "cdk deploy AssocStack --require-approval never",
                        "cdk deploy TagOptionStack --require-approval never",
                        "cdk deploy ProductStack --require-approval never",
                        "cdk deploy PortfolioStack --require-approval never",
                        "cdk deploy AssocStack --require-approval never"
                    ]
                }
            }
        }
        catalog_build_project = codebuild.PipelineProject(
            self, "BuildCatalog",
            build_spec=codebuild.BuildSpec.from_object(catalog_buildspec),
            environment_variables={
                "CATALOG_CDK_APP_S3URL": codebuild.BuildEnvironmentVariable(
                    value=catalog_cdk_app.s3_object_url),
                "MODEL_FILENAME": codebuild.BuildEnvironmentVariable(
                    value=model_filename)
            },
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0),
            role=buildprojectrole
        )
        catalog_build_action = codepipeline_actions.CodeBuildAction(
            project=catalog_build_project,
            action_name="BuildCatalog",
            input=parse_output_model,
            run_order=1
        )

        # # ---------- Accept Share
        # sharelambdarole = iam.Role(
        #     self, "ShareLambdaExecRole",
        #     assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        #     managed_policies=[managed_admin_policy]
        # )

        # share_lambda = lambda_.Function(
        #     self, 'ShareLambda',
        #     runtime=lambda_.Runtime.PYTHON_3_9,
        #     code=lambda_.Code.from_asset('idp/assets/functions/share'),
        #     handler="index.handler",
        #     role=sharelambdarole,
        #     timeout=Duration.seconds(120),
        #     environment={
        #         "REGION": Aws.REGION,
        #         "MODEL_FILENAME": model_filename,
        #         "ACCOUNTS_XACC_ROLE_NAME": spoke_xacc_role
        #     }
        # )
        # share_output = codepipeline.Artifact()
        # accept_share_action = codepipeline_actions.LambdaInvokeAction(
        #     action_name="acceptshare",
        #     inputs=[parse_output_model],
        #     lambda_=share_lambda,
        #     run_order=2,
        #     outputs=[share_output]
        # )

        # # ---------- Principals
        # principalslambdarole = iam.Role(
        #     self, "PrincipalsLambdaExecRole",
        #     assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        #     managed_policies=[managed_admin_policy]
        # )

        # principals_lambda = lambda_.Function(
        #     self, 'PrincipalsLambda',
        #     runtime=lambda_.Runtime.PYTHON_3_9,
        #     code=lambda_.Code.from_asset('idp/assets/functions/principals'),
        #     handler="index.handler",
        #     role=principalslambdarole,
        #     timeout=Duration.seconds(120),
        #     environment={
        #         "REGION": Aws.REGION,
        #         "MODEL_FILENAME": model_filename,
        #         "ACCOUNTS_XACC_ROLE_NAME": spoke_xacc_role
        #     }
        # )
        # principals_output = codepipeline.Artifact()
        # principals_action = codepipeline_actions.LambdaInvokeAction(
        #     action_name="principals",
        #     inputs=[parse_output_model],
        #     lambda_=principals_lambda,
        #     run_order=3,
        #     outputs=[principals_output]
        # )

        pipeline.add_stage(
            stage_name="BuildCatalog",
            actions=[
                catalog_build_action,
                # accept_share_action,
                # principals_action
            ]
        )
