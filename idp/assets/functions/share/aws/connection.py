import boto3


class Session(boto3.session.Session):
    _SESSION = None
    
    def __call__(cls) -> boto3.session.Session:
        if not cls._SESSION:
            cls._SESSION = boto3.session.Session()
        return cls._SESSION


def client(service_name:str) -> boto3.client:
    session = Session()
    return session().client(service_name)


def resource(service_name:str) -> boto3.resource:
    session = Session()
    return session().resource(service_name)


class SpokeSession(boto3.session.Session):
    
    def __init__(self, role_name, account_id, region_name):
        sts_client = client('sts')
        role_arn = 'arn:aws:iam::{account_id}:role/{role_name}'.format(
            account_id=account_id,
            role_name=role_name
        )
        response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName=str(account_id)
        )
        super().__init__(
            region_name=region_name,
            aws_access_key_id=response['Credentials']['AccessKeyId'],
            aws_secret_access_key=response['Credentials']['SecretAccessKey'],
            aws_session_token=response['Credentials']['SessionToken']
        )