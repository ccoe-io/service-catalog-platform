import boto3


class Session():
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