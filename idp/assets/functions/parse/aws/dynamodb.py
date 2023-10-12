from os import environ
from typing import List
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from logger import logger
from aws.connection import resource

TABLE_ARN = environ['CATALOG_TABLE_NAME']


class VersionTable():

    def __init__(self, table_name) -> None:
        self.table = resource('dynamodb').Table(table_name)

    def get_versions_product(self, product_id: str) -> list:
        response = self.table.query(
            ConsistentRead=False,
            ScanIndexForward=False,
            KeyConditionExpression=Key('product_id').eq(
                product_id) & Key('label').gte('v.0.0')
        )
        return response['Items']

    def save_versions(self, versions: List[dict]) -> None:
        with self.table.batch_writer(overwrite_by_pkeys=['product_id', 'label']) as batch:
            for ver in versions:
                batch.put_item(Item=ver)

       

    # def is_exist(self, product_id: str, md5: str) -> bool:
    #     response = self.table.query(
    #         ConsistentRead=False,
    #         KeyConditionExpression=Key('product_id').eq(
    #             product_id) & Key('label').gte('v.0.0'),
    #         FilterExpression=Key('md5').eq(md5)
    #     )
    #     return True if len(response['Items']) else False

    # def create(self, region) -> None:
    #     logger.info("all self attr before create: {}".format(self.__dict__))
    #     item = {
    #         "product_id": self.prduid,
    #         "minor": self.next_minor(),
    #         "major": self.next_major(),
    #         "label": self.next_label(),
    #         "description": self.description,
    #         "md5": self.md5,
    #         "template_url": self.upload(self.base_path+self.template_file),
    #         "role_name": self.role_prefix+'-'+region,
    #         "enabled": True,
    #         "meta": {
    #             "Name": self.product_name,
    #             "Description": self.manifest.get('Description', '--'),
    #             "Distributor": self.manifest.get('Distributor', '--'),
    #             "Owner": self.manifest.get('Owner', '--'),
    #             "SupportDescription": self.manifest.get('SupportDescription', '--'),
    #             "SupportEmail": self.manifest.get('SupportEmail', 'support@example.com'),
    #             "SupportUrl": self.manifest.get('SupportUrl', 'https://support.example.com')
    #         },
    #         "tag_options": self.tag_options
    #     }
    #     if self.role_file:
    #         item['role_url'] = self.upload(self.role_file)
    #     if self.email_file:
    #         item['email_template_url'] = self.upload(
    #             self.base_path+self.email_file)
    #     if self.macro:
    #         item['macro_urls'] = [
    #             {
    #                 "template": self.upload(self.base_path+mcro['Template']),
    #                 "package": self.uploadzip(mcro['Function'])
    #             } for mcro in self.macro]
    #     if self.custom_resource:
    #         item['cr_urls'] = [
    #             {
    #                 "template": self.upload(self.base_path+cr['Template']),
    #                 "package": self.uploadzip(cr['Function'])
    #             } for cr in self.custom_resource]

    #     self.table.put_item(Item=item)

    # def update(self, region) -> None:
    #     logger.info("all self attr before create: {}".format(self.__dict__))
    #     expression_attribute_names = {
    #         '#MD': 'meta',
    #         '#TO': 'tag_options',
    #         '#DE': 'description',
    #         '#RN': 'role_name'
    #     }
    #     expression_attribute_values = {
    #         ':md': {
    #             "Name": self.product_name,
    #             "Description": self.manifest.get('Description', '--'),
    #             "Distributor": self.manifest.get('Distributor', '--'),
    #             "Owner": self.manifest.get('Owner', '--'),
    #             "SupportDescription": self.manifest.get('SupportDescription', '--'),
    #             "SupportEmail": self.manifest.get('SupportEmail', 'support@example.com'),
    #             "SupportUrl": self.manifest.get('SupportUrl', 'https://support.example.com')
    #         },
    #         ':t': self.tag_options,
    #         ':de': self.description,
    #         ':rn': self.role_prefix+'-'+region
    #     }

    #     update_item = ['#MD = :md', '#TO = :t', '#DE = :de', '#RN = :rn']
    #     if self.role_file:
    #         expression_attribute_names['#RU'] = 'role_url'
    #         expression_attribute_values[':ru'] = self.upload(self.role_file)
    #         update_item.append('#RU = :ru')
    #     if self.email_file:
    #         expression_attribute_names['#ET'] = 'email_template_url'
    #         expression_attribute_values[':et'] = self.upload(
    #             self.base_path+self.email_file)
    #         update_item.append('#ET = :et')
    #     if self.macro:
    #         expression_attribute_names['#MU'] = 'macro_urls'
    #         expression_attribute_values[':mu'] = [
    #             {
    #                 "template": self.upload(self.base_path+mcro['Template']),
    #                 "package": self.uploadzip(mcro['Function'])
    #             } for mcro in self.macro]
    #         update_item.append('#MU = :mu')
    #     if self.custom_resource:
    #         expression_attribute_names['#CR'] = 'cr_urls'
    #         expression_attribute_values[':cr'] = [
    #             {
    #                 "template": self.upload(self.base_path+cr['Template']),
    #                 "package": self.uploadzip(cr['Function'])
    #             } for cr in self.custom_resource]
    #         update_item.append('#CR = :cr')

    #     self.table.update_item(
    #         Key={'product_id': self.prduid, 'label': self.label},
    #         ExpressionAttributeNames=expression_attribute_names,
    #         ExpressionAttributeValues=expression_attribute_values,
    #         UpdateExpression='SET '+', '.join(update_item)
    #     )

versions_table = VersionTable(TABLE_ARN)