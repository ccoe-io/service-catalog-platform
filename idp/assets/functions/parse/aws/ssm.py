from os import environ
import json
from botocore.exceptions import ClientError
from logger import logger
from aws.connection import client

ACCOUNTS_SSM_PARAMETER_NAME = environ['ACCOUNTS_SSM_PARAMETER_NAME']


class AccountsParamStore():

    def __init__(self, param_name) -> None:
        self.ssm_client = client('ssm')
        self.name = param_name

    def get(self) -> list:
        response = self.ssm_client.get_parameter(Name=self.name)
        return json.loads(response['Parameter']['Value'])

    def save(self, accounts: list) -> None:
        self.ssm_client.put_parameter(
            Name=self.name, 
            Value=json.dumps(accounts),
            Overwrite=True
        )


accounts_state = AccountsParamStore(ACCOUNTS_SSM_PARAMETER_NAME)