from botocore.exceptions import ClientError
from logger import logger
from aws.connection import client
import jmespath

organizations_client = client('organizations')


def is_tag_in_tags(tags: list, tag: dict) -> bool:
    tag_key = tag['Key']
    exist_values = jmespath.search(f"[?Key=='{tag_key}'].Value", tags)
    if tag['Value'] in exist_values:
        return True

def is_resource_tagged(resource_id: str, tag: dict) -> bool:
    paginator = organizations_client.get_paginator('list_tags_for_resource')
    response_iterator = paginator.paginate(
        ResourceId=resource_id,
        PaginationConfig={
            'MaxItems': 50
        }
    )
    for response in response_iterator:
        tags = response['Tags']
        if is_tag_in_tags(tags, tag):
            return True
    return False


paginator = organizations_client.get_paginator('list_organizational_units_for_parent')

paginator = organizations_client.get_paginator('list_accounts_for_parent')
response_iterator = paginator.paginate(
    ParentId='string',
    PaginationConfig={
        'MaxItems': 123,
        'PageSize': 123,
        'StartingToken': 'string'
    }
)