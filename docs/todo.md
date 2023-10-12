# 28-06-2022
## IDP main stack
### Enhancements
1. **Tag options** for products and portfolios
1. **Remove portfolios/products**/dependencies
1. **Versions** are indicated in the product manifet and provisioned accordingly
1. **Sharing** portfolios with org/external accounts and accept share
1. Sending **email notification** to consumer
1. Documentation -
  1. Implementation guide
1. **Pre-provisioned launch roles** - if a launch role name is explicitly indicated in the manifest, launch role is assumed to be provisioned in the spoke account.
1. Manifests validation - add first step to pipeline
1. Templates scanning - add cfn-nag/cfn-guard/cfn-lint scanning
1. SDLC with approval - embed pull request to the main branch
2. Update product/version metadata like SupportUrl/Name... etc.

### Improvements
1. Execution roles of pipeline/codebuild/lambda - adjust codepipeline role and codebuild projects roles (currently works with admin)
1. Testing results - add last pipeline step to query the portfolios and verify the desired state

### Refactoring
1. Accounts step: get all accounts from organizations and prepare SSM parameter with all the information
1. Create SSM Parameter with a list of all accounts to be connected to the event bus - use portfolios manifest
1. Move all buildspecs to the main idp stack - inbound
   move all scripts to the main idp stack and push them to idp s3; and pull them in the buildspec
   move catalog cdk app to main idp stack and upload it to s3; and pull it in the buildspec

### Bugs
1. if the main product template is not changed the dependencies will not be uploaded
1. start dependencies deployment only when dependencies are changed
1. Increase the maximum builds in the deploy dependencies codebuild batch
1. version description is not appearing
2. removing a product fails because of CFN Output exports dependency with portfolio stack