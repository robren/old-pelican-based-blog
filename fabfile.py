from fabric.api import *
import fabric.contrib.project as project
import os
import shutil
import sys
import SocketServer
import subprocess

from pelican.server import ComplexHTTPRequestHandler

# Local path configuration (can be absolute or relative to fabfile)
env.deploy_path = 'output'
DEPLOY_PATH = env.deploy_path

# Remote server configuration
production = 'root@localhost:22'
dest_path = '/var/www'

# Rackspace Cloud Files configuration settings
env.cloudfiles_username = 'my_rackspace_username'
env.cloudfiles_api_key = 'my_rackspace_api_key'
env.cloudfiles_container = 'my_cloudfiles_container'

# Github Pages configuration
env.github_pages_branch = "gh-pages"

# Docker configuration
env.docker_image = "robsblogimage"
env.docker_container_name = "robsblog"

# Port for `serve`
PORT = 8000

def clean():
    """Remove generated files"""
    if os.path.isdir(DEPLOY_PATH):
        shutil.rmtree(DEPLOY_PATH)
        os.makedirs(DEPLOY_PATH)

def build():
    """Build local version of site"""
    local('pelican -s pelicanconf.py')

def rebuild():
    """`clean` then `build`"""
    clean()
    build()

def regenerate():
    """Automatically regenerate site upon file modification"""
    local('pelican -r -s pelicanconf.py')

def serve():
    """Serve site at http://localhost:8000/"""
    os.chdir(env.deploy_path)

    class AddressReuseTCPServer(SocketServer.TCPServer):
        allow_reuse_address = True

    server = AddressReuseTCPServer(('', PORT), ComplexHTTPRequestHandler)

    sys.stderr.write('Serving on port {0} ...\n'.format(PORT))
    server.serve_forever()

def reserve():
    """`build`, then `serve`"""
    build()
    serve()

def preview():
    """Build production version of site"""
    local('pelican -s publishconf.py')


def docker_rebuild():
    """`Rebuild the  blog  for production along with  docker image : Kills  and restarts the container`"""
    clean()
    preview() # Builds the production version of the blog
    #build()

    # resorting to subprocess module calls since using the fabric.local command result
    # in insane amounts of escaping to get the {{ }} passed to the docker inspect  command
    # A number of steps are taken to avoid cruft(tm) building up on the docker  host
        # Check if there's an existing container running; if so kill it
        # Remove any existing container image, if it exists
        # Remove the existing docker image
    if subprocess.check_output("docker ps -a | grep %s; exit 0" % env.docker_container_name, shell=True) != "" :
        result = subprocess.check_output("docker inspect -f {{.State.Running}} %s" % env.docker_container_name, shell=True)
        if result .strip()== "true":
            local("docker kill  {docker_container_name}".format(**env))
        result = subprocess.check_output("docker inspect -f {{.State.Status}} %s ; exit 0" % env.docker_container_name, shell=True)
        if result.strip() == "exited":
            local("docker rm  {docker_container_name}".format(**env))
    if subprocess.check_output("docker images | grep %s; exit 0" % env.docker_image, shell=True) != "" :
        local("docker rmi  {docker_image}".format(**env))
    local("docker build -t {docker_image} .".format(**env))
    local("docker run -d -p 80:80 --name {docker_container_name} {docker_image} ".format(**env))



def cf_upload():
    """Publish to Rackspace Cloud Files"""
    rebuild()
    with lcd(DEPLOY_PATH):
        local('swift -v -A https://auth.api.rackspacecloud.com/v1.0 '
              '-U {cloudfiles_username} '
              '-K {cloudfiles_api_key} '
              'upload -c {cloudfiles_container} .'.format(**env))

@hosts(production)
def publish():
    """Publish to production via rsync"""
    local('pelican -s publishconf.py')
    project.rsync_project(
        remote_dir=dest_path,
        exclude=".DS_Store",
        local_dir=DEPLOY_PATH.rstrip('/') + '/',
        delete=True,
        extra_opts='-c',
    )

def gh_pages():
    """Publish to GitHub Pages"""
    rebuild()
    local("ghp-import -b {github_pages_branch} {deploy_path}".format(**env))
    local("git push origin {github_pages_branch}".format(**env))
