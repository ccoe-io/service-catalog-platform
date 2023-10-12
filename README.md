Note: need to update for use of cdk pipelines pieline and cross account deployment, where the source for the catalog is
an s3 in the deployment account.
1. Both accounts should be bootstrapted with CDK:
    1. Deployment account: `cdk bootstrap`
    1. Target account: `cdk bootstrap --trust <deployments-account-id> aws://<target-account-id>/<target-region> --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess`
## Overview
This repository contains a CDK app which describes a codepipeline pipeline which provisions the different resources of a catalog.

## Deployment
### Management account - Only relevant if using AWS_Organization sharing method.
1. AWS Organizations and AWS Service Catalog integration is enabled.
1. Deploy a cross account role to allow read of all organization accounts/OUs/tags.
This role will be deployed to the account-management delegated administrator.
To define a delegated admin for account management:
```bash
aws organizations register-delegated-administrator \
    --account-id 012345678901 \
    --service-principal account.amazonaws.com
```
### Hub Account
1. Select the hub account -  a dedicated AWS Account (may be a shared services account)
1. The account is setup as delegated administrator for service catalog - Only relevant if using AWS_Organization sharing method.
```bash
aws organizations register-delegated-administrator \
    --account-id 012345678901 \
    --service-principal servicecatalog.amazonaws.com
```

### Spoke Accounts
1. Deploy a cross account role in each member account. This role will be assumed from the hub account by the pipeline to deploy product dependencies, accept portfolios share and add principals to the imported portfolios. Use the template under `xacc-role-template` to provision the role.
1. Make sure to deploy the same role to the Hub Account as well.
1. The CFN template of the recomended role can be found at `docs/xacc-role-template/`

### Update CDK parameters
```json
    "SOURCE": { <The details of the solution repository - either S3 or git repo>
      "s3": {
        "bucket_name": "",
        "bucket_key": ""
      },
      "git": {
        "repo": "<full repository path>",
        "branch": "<branch>",
        "connection_arn_ssm_parameter": "<the name of an ssm parameter that holds the codestar connection arn>"
      }
    },
    "CATALOG_SOURCE": { <The details of the catalog definition repository - either S3 or git repo>
      "s3": {
        "bucket_name": "",
        "bucket_key": ""
      },
      "git": {
        "repo": "<full repository path>",
        "branch": "<branch>",
        "connection_arn_ssm_parameter": "<the name of an ssm parameter that holds the codestar connection arn>"
      }
    },
    "SPOKE_XACC_ROLE": "<The name of the cross account role which deployed to spoke accounts>",
    "SSM_PARAM_NAME_ORG_ID": "<the name of an ssm parameter that holds the organization id>",
    "DEPLOYMENT_TARGET": {
        "account_id": "",
        "region": ""
    }
```
### Pipeline source - Catalog Repository
The source for this pipeline is a repository that includes all the Portfolios and Products description (manifests).
The structure of the sources repository must have `products` folder and `portfolios` folder on its root level.
```bash
.
├── portfolios
│   └── <portfolio-folder>
│   │   │── manifest.yml
│   └── <portfolio-folder>
│       └── manifest.yml
└── products
    ├── <product-folder>
    │   ├── diagram.png
    │   ├── email-template.json
    │   ├── manifest.yml
    │   ├── permissions.json
    │   ├── README.md
    │   └── template.yml
    └── <product-folder>
        ├── diagram.png
        ├── email-template.json
        ├── manifest.yml
        ├── permissions.json
        ├── README.md
        └── template.yml
```
1. Choose the source: for codepipeline the source can be bitbucket/github/codecommit repository or an S3 bucket. 
1. Select your catalog source and update the `idp/idp_stack.py` with the desired source.

### Deploy the solution
1. clone the source of the platform (this) repository.
1. change directory to the cloned repository.
1. run `cdk` cli:
```bash
pip3 install -r requirements.txt
cdk bootstrap
cdk deploy IdpStack \
   --parameters SrcBucket=<S3 Bucket Name that stores the catalog source> \
   --parameters SrcKey=<S3 Key name of the source archive> \
   --parameters OrgId=<AWS Organizations org id> \
   --parameters SpokeRole=<Cross Account Spoke Role Name>
```

## Architecture

![Architecture](docs/main-pipeline.png)

1. The codepipeline pipeline starting point. The pipeline is invoked by the source code catalog-repository push events.
2. In the catalog-repository, service catalog products and service catalog portfolios are described in a declarative manner using yaml files.
3. After Source the next step is a codebuild project which scans the cloudformation templates.
4. In this step a lambda function processes the manifests and:
5. determines the desired state for products and their versions and stores it in a dynamodb table.
6. determines The desired state for portfolios and stores in an SSM Parameter store.
7. uploads templates or other artifacts to the dedicated catalog s3 bucket. A product definition will point to the objects in this bucket, and when deploying dependencies the artifacts (cfn, source) will be expected to reside in this bucket. 
8. In addition, the lambda #4, renders the buildspec yml for the dependencies step, in which a codebuild batch jobs deploys required roles (launch roles), custom resources, and macros to the target member/spoke accounts.
9. Run the cdk application of the catalog. This creates 2 stacks, the products stack and the portfolios stack.
10. After the products and portfolios were created on #9, and the portfolios were shared with the spoke accounts, at #10 a lambda function will assume xacc role in the spokes and will accept the share from the hub account.
11. Finally, access need to be determined for each portfolio in each spoke account, which is done again by a lambda that assumes role in the spoke accounts.
