from os import chdir, path
import zipfile
import tempfile
from boto3.session import Session
import botocore
from botocore.exceptions import ClientError
from logger import logger
from aws.connection import client

code_pipeline = client('codepipeline')


def download_input_artifact(event):
    chdir('/tmp')
    s3 = setup_s3_client(event)
    input_artifact = event['CodePipeline.job']['data']['inputArtifacts'][0]
    bucket = input_artifact['location']['s3Location']['bucketName']
    key = input_artifact['location']['s3Location']['objectKey']
    with tempfile.NamedTemporaryFile() as tmp_file:
        s3.download_file(bucket, key, tmp_file.name)
        with zipfile.ZipFile(tmp_file.name, 'r') as zip:
            zip.extractall()


def upload_output_artifact(event: dict, artifact_index: int, *args):
    job_data = event['CodePipeline.job']['data']
    output_artifact = job_data['outputArtifacts'][artifact_index]
    output_bucket = output_artifact['location']['s3Location']['bucketName']
    output_key = output_artifact['location']['s3Location']['objectKey']
    s3 = setup_s3_client(event)
    with tempfile.NamedTemporaryFile() as tmp_file:
        with zipfile.ZipFile(tmp_file.name, 'w') as ziph:
            for file_path in args:
                file_path = path.abspath(file_path)
                ziph.write(file_path, path.basename(file_path))
        s3.upload_file(tmp_file.name, output_bucket, output_key)


def setup_s3_client(event):
    job_data = event['CodePipeline.job']['data']
    key_id = job_data['artifactCredentials']['accessKeyId']
    key_secret = job_data['artifactCredentials']['secretAccessKey']
    session_token = job_data['artifactCredentials']['sessionToken']

    session = Session(
        aws_access_key_id=key_id,
        aws_secret_access_key=key_secret,
        aws_session_token=session_token
    )
    return session.client(
        's3', config=botocore.client.Config(signature_version='s3v4'))


def put_job_success(job, message):
    logger.info('Putting job success')
    logger.info(message)
    code_pipeline.put_job_success_result(jobId=job)


def put_job_failure(job, message):
    logger.info('Putting job failure')
    logger.info(message)
    code_pipeline.put_job_failure_result(
        jobId=job, failureDetails={'message': message, 'type': 'JobFailed'})