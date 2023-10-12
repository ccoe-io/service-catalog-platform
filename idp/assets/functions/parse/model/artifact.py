from dataclasses import dataclass, field, InitVar
import os
import subprocess
import sys
from logger import logger
from botocore.exceptions import ClientError
from aws.connection import resource
from utils import calculate_file_md5

S3_ARTIFACTS_REGION = os.environ['CATALOG_ARTIFACTS_BUCKET_REGION']


@dataclass
class Template():
    s3bucket: str
    s3prefix: InitVar[str]
    local_path: InitVar[str]
    mid: str = None
    s3key: str = None
    _s3url: str = None

    def __post_init__(self, s3prefix: str, local_path: str) -> None:
        self.s3prefix = s3prefix
        self.local_path = local_path
        self.s3key = os.path.join(self.s3prefix, os.path.basename(self.local_path))

        self._is_modified = None
        self._is_exists = None
        self._s3_object = None

        self.verify_local_artifact()

        self.s3_resource = resource('s3')

    @property
    def s3_object(self):
        if not self._s3_object:
            self._s3_object = self.s3_resource.Object(
                self.s3bucket,
                self.s3key
            )
        return self._s3_object

    @property
    def s3url(self) -> str:
        # if not self._s3url:
        self._s3url = self.get_version_url()
        return self._s3url

    @property
    def is_modified(self) -> str:
        # if not self._is_modified:
        self._is_modified = self.get_modified()
        return self._is_modified

    @property
    def is_exists(self) -> str:
        # if not self._is_exists:
        self._is_exists = self.get_exists()
        return self._is_exists

    def verify_local_artifact(self) -> str:
        if not os.path.isfile(self.local_path):
            raise(FileNotFoundError(
                f'either {self.local_path} not exist or '+
                f'specified path is not a file'))

    def get_version_url(self) -> str:
        if self.is_exists:
            return 'https://{bucket}.s3.{region}.amazonaws.com/{key}?versionId={ver}'.format(
                bucket=self.s3bucket,
                region=S3_ARTIFACTS_REGION,
                key=self.s3key,
                ver=self.s3_object.version_id
            )

    def get_exists(self) -> bool:
        try:
            self.s3_object.version_id
            return True
        except ClientError as err:
            if err.response['Error']['Code'] != '404':
                raise(err)
            return False

    def get_modified(self) -> bool:
        if not self.is_exists:
            return True
        md5 = calculate_file_md5(self.local_path)
        etag = self.s3_object.e_tag.strip('\"')
        if str(md5) == etag.strip('"'):
            return False
        return True

    def package(self) -> str:
        logger.debug(f'Package: {self.local_path}')
        output_file = os.path.abspath('packaged.yml')
        try:
            # run_path = os.path.abspath('.')
            # dir_path = os.path.dirname(os.path.abspath(self.local_path))
            # os.chdir(dir_path)
            parameters = [
                '--template-file', self.local_path,
                '--s3-bucket', self.s3bucket,
                '--s3-prefix', 'packaged-code',
                '--output-template-file', output_file
            ]
            args = ['/opt/awscli/aws'] + ['cloudformation'] + ['package'] + parameters
            subproc_res = subprocess.run(args)
            logger.debug('subprocess run completed {}'.format(subproc_res))
            # os.chdir(run_path)
        except subprocess.CalledProcessError as err:
            sys.exit(err.returncode)
        self.local_path = output_file

    def upload(self) -> None:
        if self.is_modified:
            logger.debug(f'Upload: {self.local_path}')
            self.s3_object.upload_file(self.local_path)
        self.s3_object.reload()
        self.mid = self.s3_object.version_id
