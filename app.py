import calendar
import os
import shutil
from datetime import date
from pathlib import Path

import pdfkit as pdfkit
from flask import Flask, render_template, request, send_file
from urllib.parse import urlparse

app = Flask(__name__)

dl_filename = 'ClassGroupAudit.zip'
pdf_path = 'ClassGroupAudit'


@app.route('/', methods=['GET', 'POST'])
def home():
    url_list = None
    bad_urls = []
    if request.method == 'POST':
        urls = request.values.get('urls')
        url_list = urls.split()
        bad_urls = create_pdf(url_list)

    # if the intended zip file exists at the root, allow the user to download
    download_link = None
    if os.path.isfile(dl_filename):
        download_link = '/download'  # matches the route in the application

    return render_template(
        'home.html',
        urls=url_list,
        bad_urls=bad_urls,
        download_link=download_link
    )


@app.route('/download')
def downloadFile ():
    path = f"{dl_filename}"
    return send_file(path, as_attachment=True)


def uri_validator(x):
    try:
        result = urlparse(x)
        return all([result.scheme, result.netloc])
    except:
        return False


def get_name(url):
    parsed = urlparse(url)
    path = parsed.path[1:]
    second_slash = path.find('/')
    if second_slash > 0:
        path = path[:second_slash]
    return f'{path}.pdf'


def create_pdf(url_list):
    bad_urls = []

    # Create the necessary pdf_path
    Path(pdf_path).mkdir(parents=True, exist_ok=True)

    for url in url_list:
        # ensure https:// is at front of urls
        if url[0:3] == 'www':
            url = f'https://{url}'

        # Verify the url is valid (otherwise give output)
        if not uri_validator(url):
            bad_urls.append(url)
        else:
            filename = get_name(url)
            pdfkit.from_url(
                url,
                output_path=os.path.join(pdf_path, filename)
            )
        return bad_urls

    # pdfs are done. Zip them up and put them in a predictable location
    if len(os.listdir(pdf_path)) > 0:
        shutil.make_archive(dl_filename.replace('.zip', ''), format='zip', root_dir=pdf_path)


if __name__ == '__main__':
    app.run()
