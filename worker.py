import os
import shutil
from pathlib import Path
from urllib.parse import urlparse

import botocore.exceptions
from dotenv import load_dotenv
from weasyprint import HTML, CSS

load_dotenv()

from app import queue, pdf_worker_key, pdf_path, dl_filename, s3, s3_bucket


def create_pdfs_from_queue():
    for i in range(0, queue.llen(pdf_worker_key)):
        url = queue.lpop(pdf_worker_key)
        try:
            filename = get_name(url)
            # Custom CSS to clean up mistakes in HTML and add the filename to the header
            css = CSS(string='''
                @page {
                    size: 315mm 445.5mm; margin: .5in .1in;
                    @top-left {
                        content: "'''+filename.replace('.pdf','')+'''";
                        font-size: 2em;
                    }
                }
                .noscript{display: none !important;}
                .skip-link{display: none !important;}
                .headerStatusLine{visibility: hidden;}
                .foldout a.cssa img{display: none !important;}
                br{clear:both;display:block;}
            ''')
        
            pdf_bytes = HTML(url).write_pdf(stylesheets=[css])
            s3.put_object(Body=pdf_bytes, Bucket='uline-pdfs', Key=filename, ContentType='application/pdf')
        except:
            queue.rpush(pdf_worker_key, url)  # put this back in the list if there is an issue


def zip_bucket(bucket_name='uline-pdfs'):
    files_to_zip = []
    response = s3.list_objects_v2(Bucket=bucket_name)

    all = response['Contents']
    for i in all:
        files_to_zip.append(str(i['Key']))

    for KEY in files_to_zip:
        try:
            local_file_name = f'{pdf_path}/{KEY}'
            s3.download_file(bucket_name, KEY, local_file_name)
        except Exception as e:
            print(e)

    # now create empty zip file in /tmp directory use suffix .zip if you want
    shutil.make_archive(dl_filename.replace('.zip', ''), format='zip', root_dir=pdf_path)
    s3.upload_file(dl_filename, Bucket=bucket_name, Key='ClassGroupAudit.zip')


def get_name(url):
    parsed = urlparse(url)
    path = parsed.path[1:]
    second_slash = path.find('/')
    if second_slash > 0:
        path = path[:second_slash]
    return f'{path}.pdf'


if __name__ == '__main__':
    if queue.llen(pdf_worker_key) > 0:
        create_pdfs_from_queue()
    else:
        # There is nothing in the queue. Update the zip file if one doesn't exist
        try:
            response = s3.head_object(
                Bucket=s3_bucket,
                Key=dl_filename
            )
        except botocore.exceptions.ClientError:
            Path(pdf_path).mkdir(parents=True, exist_ok=True)
            zip_bucket()

