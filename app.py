import os

import boto3
import redis
from flask import Flask, render_template, request, send_file, redirect, url_for
from urllib.parse import urlparse

app = Flask(__name__)
dl_filename = '/tmp/ClassGroupAudit.zip'
pdf_path = '/tmp/ClassGroupAudit'

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
        if os.path.isfile(dl_filename):
            os.remove(dl_filename)  # remove the existing zip file
        return redirect(url_for('home'), code=302)

    # if the intended zip file exists at the root, allow the user to download
    download_link = None
    if os.path.isfile(dl_filename):
        download_link = '/download'  # matches the route in the application

    # if there are bad urls report on them once
    bad_urls = []
    if queue.llen(bad_url_key) > 0:
        for i in range(queue.llen(bad_url_key)):
            bad_urls.append(queue.lpop(bad_url_key))

    return render_template(
        'home.html',
        url_count=queue.llen(pdf_worker_key),
        bad_urls=bad_urls,
        download_link=download_link
    )


# The route that downloads the zipped up PDFs
@app.route('/download')
def download():
    return send_file(dl_filename, as_attachment=True)


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


if __name__ == '__main__':
    app.run()
