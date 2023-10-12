## Product manifest specification
```bash
# Single product manifest.yml
Id: <unique id> # [aZ09]
ExistLaunchRoleName: # When not provided a new role will be created sc-launch-{product-id}-{region}

Name: <display name of the product in service catalog> # []
Description: <>
Distributor: <>
Owner: <>
SupportDescription: <>
SupportEmail: <must be valid email format>
SupportUrl: <must be valid url format>

TagOptions:
  - Key: tagkey1
    Values:
    - allowed_value1
    - allowed_value2
    - allowed_valueN
  - Key: tagkey2
    Values:
    - allowed_value1
    - allowed_value2
    - allowed_valueN

Artifacts:
  Template: <relative file path>
  LaunchRolePermissions: <relative file path>
  EmailNotificationTemplate: <relative file path>

Dependencies:
  - <dependency-id>
  - <dependency-id>

# Current version description
VersionDescription: <current version description>
VersionOption: <Major/Minor/Override> the latter will leave the current version unchanged

# Additional Versions
# Make sure that dependencies (LaunchRole, CR, Macro) are backwards compatible
# The following values are valid:
# "THIS" is the current published version
# "THIS-<index>" where index is "<major>.<minor>"; if minor not specified, the latest minor will be used
# "vx.y" explicit version label
Versions:
  - THIS # current version
  - THIS-1 # previous version by index
  - v1.5 # explicit version

```

## Launch Role Permissions
This file should include the permissions required to deploy the resources of the product.
The permissions are stated in json format and according to [managed policies](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-iam-role.html#cfn-iam-role-managepolicyarns) and [policies](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-iam-role.html#cfn-iam-role-policies)
The structure of the json will be:
```json
"Policies": []
"ManagedPolicyArns" []
```
