## Portfolio manifest specification
```bash
# Single portfolio manifest.yml

Id: <unique id>
Name: <display name of the portfolio in service catalog>
ProviderName: <>
Description: <>

Products:
  - <product-id>
  - <product-id>

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

Principals:
  - SelectorType: RoleName # Only IAM Roles are currently supported
    Values:
      - <full path><role name> wildcard Role accepts values with a "*" or "?"
      - ResourceName_*
      - */ResourceName_?
      - aws-reserved/sso.amazonaws.com/AWSReservedSSO_ReadOnlyAccess*
  - SelectorType: ARN # Not Supported
    Values:
      - <full name>
      - <substring>
  - SelectorType: Tags # Not supported
    Values:
      - <key>: <value>
      - <key>: <value>

Shares:
  - SelectorType: AccountsIds
    Values:
      - <account-id>
      - <account-id>
  - SelectorType: Tags # Not supported
    Values:
      - <key>: <value>
      - <key>: <value>
  - SelectorType: AccountsNames # Not supported
    Values:
      - <account-name>
      - <account-name>
  - SelectorType: OrgUnitsIDs # Not supported
    # Temporary not supported in favor of supporting AMS accounts
    # Nested OUs not supported
    Values:
      - <ou-id>
      - <ou-id>
  - SelectorType: OrgUnitsNames # Not supported
    # Nested OUs not supported
    Values:
      - <ou-path>/<ou-name>
      - <ou-path>/<ou-name>
```
