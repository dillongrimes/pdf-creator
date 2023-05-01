import os
import boto3
import botocore.exceptions
import pytz as pytz
import redis
from flask import Flask, render_template, request, redirect, url_for
from urllib.parse import urlparse

app = Flask(__name__)
tmp_path = '/tmp'
dl_filename = 'ClassGroupAudit.zip'
dl_filepath = os.path.join(tmp_path, dl_filename)
pdf_folder_name = 'ClassGroupAudit'
pdf_path = os.path.join(tmp_path, pdf_folder_name)

s3_bucket = 'uline-pdfs'
s3 = boto3.client(
    's3',
    aws_access_key_id=os.environ['aws_access_key_id'],
    aws_secret_access_key=os.environ['aws_secret_access_key'])

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
queue = redis.from_url(redis_url, decode_responses=True)

pdf_worker_key = 'url_list'
bad_url_key = 'bad_urls'


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        urls = request.values.get('urls')
        url_list = urls.split()
        queue_pdf_creation(url_list)
        return redirect(url_for('home'), code=302)

    download_link = None
    last_modified = None
    try:
        response = s3.head_object(
            Bucket=s3_bucket,
            Key=dl_filename
        )
        last_modified = response['LastModified']
        tz = pytz.timezone('America/Chicago')
        last_modified = last_modified.astimezone(tz)
        last_modified = last_modified.strftime('%Y-%m-%d %l:%M%p')
        download_link = s3.generate_presigned_url(
            'get_object', Params={'Bucket': s3_bucket, 'Key': dl_filename}
        )
    except botocore.exceptions.ClientError:
        pass

    # if there are bad urls report on them once
    bad_urls = []
    if queue.llen(bad_url_key) > 0:
        for i in range(queue.llen(bad_url_key)):
            bad_urls.append(queue.lpop(bad_url_key))

    return render_template(
        'home.html',
        url_count=queue.llen(pdf_worker_key),
        bad_urls=bad_urls,
        download_link=download_link,
        last_modified=last_modified
    )


def uri_validator(x):
    try:
        result = urlparse(x)
        return all([result.scheme, result.netloc])
    except:
        return False


def queue_pdf_creation(url_list):

    for url in url_list:
        # ensure https:// is at front of urls
        if url[0:3] == 'www':
            url = f'https://{url}'

        # Verify the url is valid (otherwise notify)
        if not uri_validator(url):
            queue.lpush(bad_url_key, url)
        else:
            # add to redis queue here
            queue.lpush(pdf_worker_key, url)

    if queue.llen(pdf_worker_key) > 0:
        # clear the old zip file if new urls were added
        try:
            s3.delete_object(Bucket=s3_bucket, Key=dl_filename)
        except botocore.exceptions.ClientError:
            pass


if __name__ == '__main__':
    app.run()
