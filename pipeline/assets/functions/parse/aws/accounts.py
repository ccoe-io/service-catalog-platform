from botocore.exceptions import ClientError
from logger import logger
from aws.connection import client
import jmespath

MANAGEMENT_ACCOUNT_ID = '515127908126'
organizations_client = client('organizations')


def get_member_accounts_ids(ou_id=None, tag_key=None, tag_value=None):
    accounts = get_member_accounts(ou_id=ou_id, tag_key=tag_key, tag_value=tag_value)
    return [account['Id'] for account in accounts]


def get_member_accounts(ou_id=None, tag_key=None, tag_value=None):
    if ou_id:
        return get_all_member_accounts_by_ou_id(ou_id)
    elif tag_key and tag_value:
        return get_all_member_accounts_by_tag(tag_key, tag_value)
    else:
        return get_all_member_accounts()


def get_all_member_accounts_by_ou_id(ou_id):
    member_accounts = []
    _get_member_accounts_recursive(ou_id, member_accounts)
    return jmespath.search("[?Status=='ACTIVE']", member_accounts)


def _get_member_accounts_recursive(ou_id, member_accounts):
    paginator = organizations_client.get_paginator('list_accounts_for_parent')
    response_iterator = paginator.paginate(ParentId=ou_id)

    for response in response_iterator:
        accounts = response['Accounts']
        member_accounts.extend(accounts)

    # Get the children OUs
    ou_response = organizations_client.list_organizational_units_for_parent(ParentId=ou_id)
    children_ous = ou_response['OrganizationalUnits']
    for child_ou in children_ous:
        child_ou_id = child_ou['Id']
        _get_member_accounts_recursive(child_ou_id, member_accounts)


def get_all_member_accounts_by_tag(tag_key, tag_value):
    paginator = organizations_client.get_paginator('list_accounts')
    response_iterator = paginator.paginate()

    member_accounts = []
    for response in response_iterator:
        member_accounts.extend(response['Accounts'])
    
    accounts = [account for account in member_accounts if account['Tags'].get(tag_key) == tag_value]        
    return jmespath.search("[?Status=='ACTIVE']", accounts)

def get_all_member_accounts():
    paginator = organizations_client.get_paginator('list_accounts')
    response_iterator = paginator.paginate()

    member_accounts = []
    for response in response_iterator:
        member_accounts.extend(response['Accounts'])

    return jmespath.search(f"[?Id != '{MANAGEMENT_ACCOUNT_ID}' && Status == 'ACTIVE']", member_accounts)