import os
import os.path
import subprocess

from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect

from nbhosting.settings import logger, nbhosting_settings as settings

# Create your views here.

def error_page(course, student, notebook, message=None):
    html = ""
    html += "<h1>nbhosting internal error</h1>"
    html += "<p>"
    html += "Error for course {} with student {}"\
            .format(course, student)
    html += "<br/>"
    html += "Notebook was {}".format(notebook)
    if message:
        html += "<br/>"
        html += message
    html += "</p>"
    return HttpResponse(html)

def verbatim(text):
    return "<pre><code>{}</code></pre>".format(text)

# the main edxfront entry point
def notebook_request(request, course, student, notebook):

    root = settings['root']
    # the ipynb extension is removed from the notebook name in urls.py
    notebook_full = notebook + ".ipynb"
    
    # xxx probably requires a sudo of some kind here
    # for when run from apache or nginx or whatever

    script = os.path.join(root, 'scripts/add-student-in-course')
    command = [ script, root, student, course ]
    logger.info("In {}\n-> Running command {}".format(os.getcwd(), " ".join(command)))
    completed_process = subprocess.run(
        command, universal_newlines=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logger.info("<- {}".format(completed_process))

    script = os.path.join(root, 'scripts/run-student-course-jupyter')
    command = [ script, root, student, course, notebook_full ]
    logger.info("In {}\n-> Running command {}".format(os.getcwd(), " ".join(command)))
    completed_process = subprocess.run(
        command, universal_newlines=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logger.info("<- {}".format(completed_process))

    if completed_process.returncode != 0:
        return error_page(
            course, student, notebook,
            "command {} returned {}<br/>stderr:{}"
            .format(command, completed_process.returncode,
                    verbatim(completed_process.stderr)))
    try:
        docker_name, docker_port, jupyter_token = completed_process.stdout.split()
        host = request.get_host()
        # remove initial port if present
        if ':' in host:
            host, _ = host.split(':', 1)
        url = "http://{}:{}/notebooks/{}?token={}"\
              .format(host, docker_port, notebook_full, jupyter_token)
        logger.info("edxfront: redirecting to {}".format(url))
        return HttpResponseRedirect(url)

    except Exception as e:
        return error_page(
            course, student, notebook,
            "exception when parsing output of {}<br/>{}"
            .format(script, verbatim(e)))
    