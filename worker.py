import os
import shutil
from pathlib import Path
from urllib.parse import urlparse
from weasyprint import HTML, CSS

from app import pdf_path, queue, pdf_worker_key, dl_filename


def create_pdfs_from_queue():
    # Create the necessary pdf_path
    Path(pdf_path).mkdir(parents=True, exist_ok=True)

    # CSS to clean up our junky pages
    css = CSS(string='''
        @page {size: 315mm 445.5mm; margin: .5in .1in;}
        .noscript{display: none !important;}
        .skip-link{display: none !important;}
        .headerStatusLine{visibility: hidden;}
        .foldout a.cssa img{display: none !important;}
    ''')

    for i in range(0, queue.llen(pdf_worker_key)):
        url = queue.lpop(pdf_worker_key)
        try:
            filename = get_name(url)
            HTML(url).write_pdf(os.path.join(pdf_path, filename), stylesheets=[css])
        except:
            queue.rpush(pdf_worker_key, url)  # put this back in the list if there is an issue

    # pdfs are done. Zip them up and put them in a predictable location
    if len(os.listdir(pdf_path)) > 0 and queue.llen(pdf_worker_key) == 0:
        shutil.make_archive(dl_filename.replace('.zip', ''), format='zip', root_dir=pdf_path)


def get_name(url):
    parsed = urlparse(url)
    path = parsed.path[1:]
    second_slash = path.find('/')
    if second_slash > 0:
        path = path[:second_slash]
    return f'{path}.pdf'


if __name__ == '__main__':
    create_pdfs_from_queue()
