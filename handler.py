import boto3
from botocore.client import Config
import json
import io
import zipfile
import mimetypes
import logging

def lambda_handler(event, context):

    # Set logging object
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.info(event)

    # get codebuild object
    codepipeline = boto3.client('codepipeline')

    # get sns object
    sns = boto3.resource('sns')
    topic = sns.Topic('arn:aws:sns:eu-west-1:284351314223:NotifyPortfolioBuild')

    # portfolio build bucket to use if the deployment is trigger manually
    location: {
        "bucketName": 'kike-portfolio-deployment',
        "objectKey": 'portfolio'
    }

    response = []
    response = {"message": 'All good here' }

    try:
        job = event.get('CodePipeline.job')

        if job:
            print('codepipeline event')
            logger.info(job)
            for artifact in job['data']['inputArtifacts']:
                print(artifact)
                if artifact['name'] == 'BuildArtifact':
                    location = artifact['location']['s3Location']

        # get s3 object
        s3 = boto3.resource('s3', config=Config(signature_version='s3v4'))

        portfolio_bucket = s3.Bucket('kike-portfolio')
        build_portfolio_bucket = s3.Bucket(location['bucketName'])

        # Download file from build bucket and store the objects in memory
        portfolio_zip = io.BytesIO()
        build_portfolio_bucket.download_fileobj(location['objectKey'], portfolio_zip)

        # grab objects from memory and set mimetype and then upload it to deployment bucket
        with zipfile.ZipFile(portfolio_zip) as myzip:
            for key in myzip.namelist():
                obj = myzip.open(key)
                obj_type = mimetypes.guess_type(key)[0]

                if obj_type is not None:
                    portfolio_bucket.upload_fileobj(obj,key,
                        ExtraArgs={'ContentType': obj_type })
                    portfolio_bucket.Object(key).Acl().put(ACL='public-read')

        print("Job compleated")
        topic.publish(Message='Success Portfolio has been deployed')

        if job:
            codepipeline.put_job_success_result(jobId=job['id'])

    except:
        print("Error")
        topic.publish(Message='Failed!! Portfolio has not been deployed')
        if job:
            codepipeline.put_job_failure_result(jobId=job['id'])
        raise

    logger.info(response)

    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }
