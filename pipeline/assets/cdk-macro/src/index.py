'''
The cdk synth macro returns a cloudformation template by synth a cdk
application.
Using the cdk synth macro in the cloudformation template:

Resources:
  CallTransform:
    Fn::Transform:
        Name: "CDKSynth"
        Parameters:
            cdkAppS3Bucket: ""
            cdkAppS3Prefix: ""
            cdkAppModule: ""
            cdkAppStackClass: ""
            cdkAppStackName: ""
            cdkAppEnv:
                Variables:
                    Name1: Value1
                    Name2: Value2
'''

import os
from importlib import import_module
import logging
import json
import boto3
from cfn_flip import load_json, dump_json
import aws_cdk as cdk


LOG_LOCAL_PREFIX = "handler:   "
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL', 'DEBUG'))


def handler(event, context):
    logger.info(json.dumps(event))
    # region = event['region']
    # account = event['accountId']
    cdk_app_s3_bucket = event['params']['cdkAppS3Bucket']
    cdk_app_s3_prefix = event['params']['cdkAppS3Prefix']
    module_name = event['params']['cdkAppModule']
    class_name = event['params']['cdkAppStackClass']
    stack_name = event['params']['cdkAppStackName']
    cdk_app_vars = json.loads(
        event['params'].get('cdkAppVariables', json.dumps({})))
    logger.info("Input vars: ", cdk_app_vars)
    for key, value in cdk_app_vars.items():
        os.environ[key] = value

    session = boto3.session.Session()
    cdk_path = download_cdk_app(session, cdk_app_s3_bucket, cdk_app_s3_prefix)
    logger.info(f"CDK app downloaded: {cdk_path} ")
    logger.info(f"Call CDK Synth: {module_name}, {class_name}, {stack_name}")
    # rendered_fragment = synth_cfn_template(module_name, class_name, stack_name)
    rendered_fragment = {}
    logger.info('Returned value: {}'.format(rendered_fragment))
    return {
        'requestId': event['requestId'],
        'status': 'success',
        'fragment': rendered_fragment
    }


# def synth_cfn_template(module_name, class_name, stack_name):
#     app = cdk.App(outdir="/tmp")
#
#     module = import_module(module_name)
#     class_ = getattr(module, class_name)
#
#     class_(app, stack_name)
#     app.synth()
#
#     with open(f"/tmp/{stack_name}.template.json", "r") as file:
#         template_body = file.read()
#     resources = load_json(template_body)['Resources']
#     return dump_json(resources)


def download_cdk_app(session, bucket_name, prefix):
    s3_resource = session.resource('s3')
    bucket = s3_resource.Bucket(bucket_name)
    base_path = '/tmp'
    for obj in bucket.objects.filter(Prefix=prefix):
        if obj.size == 0:
            continue
        target_path = base_path
        relative = os.path.relpath(os.path.dirname(obj.key), prefix)
        if relative != ".":
            target_path = os.path.join(base_path, relative)
        if not os.path.exists(target_path):
            os.makedirs(target_path)
        logger.info("target_path {}".format(os.path.join(target_path, os.path.basename(obj.key))))
        logger.info("Object: {}".format(obj.key))
        bucket.download_file(
            obj.key, os.path.join(target_path, os.path.basename(obj.key)))
    return target_path
