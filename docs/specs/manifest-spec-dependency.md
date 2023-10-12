## Dependency manifest specification
```bash
# Single dependency manifest.yml
Id: <unique id> # [aZ09]
Owner: <email address>
Template: <relative path>
Parameters:
    <parameter key>: Output <ref-dependency-mid>.<output name>
    <parameter key>: <Free Text>
Prerequisites:
    - <dependency-id>
    - <dependency-id>
# The permissions needed to deploy this module. Will be used to validate adequate permissions in the cross account role.
Permissions: <relative file path> # Not supported 
```

## Dependency folder
A dependency folder includes the template to deploy and any required assets. 
Assets are any packagable artifacts when using aws cloudformation [package command](https://awscli.amazonaws.com/v2/documentation/api/2.0.33/reference/cloudformation/package.html).

### Example Dependency folder with lambda code as asset:
```bash
dependencies
├── collectcfnstacks
│   ├── README.md
│   ├── app
│   │   ├── __init__.py
│   │   ├── bucket_actions.py
│   │   ├── collect_cfn_stacks.py
│   │   ├── index.py
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   └── spoke_session.py
│   ├── manifest.yml
│   └── template.yaml
```

The asset must be refered in the template with relative path. See more infomation under the cli user guide [package command](https://awscli.amazonaws.com/v2/documentation/api/2.0.33/reference/cloudformation/package.html).

## Build Custom Resources:
In order to easily refer the custom resource from the product template, it is recomended to have the lambda template define an SSM Parameter to the lambda ARN, and consume this value in the custom resource ServiceToken property via and SSM parameter dynamic reference.
