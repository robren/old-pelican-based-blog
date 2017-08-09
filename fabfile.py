from fabric.api import *
import fabric.contrib.project as project
import os
import shutil
import sys
import SocketServer
import ConfigParser

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
env.docker_blog_image = 'alpine-blog'
# migrated away from gke. 
#env.docker_blog_image = 'gcr.io/robren-blog-v1/alpine-blog:' 
env.docker_target_dir = '/usr/share/nginx/html'
env.docker_container_name = 'pelican_site_container'

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
    local("ghp-import -b {github_pages_branch} {deploy_path} -p".format(**env))

def docker_rebuild():
    """Rebuild the pelican site for production and install in a docker image :
       - Kill and remove any existing pelican_site container.
       - Copy the site into the webserver base image, build a new pelican_site
         container.
       - Run our new container.
    """
    clean()
    preview()  # Builds the production version of the site


    # Prune stopped containers and dangling old images.
    local("docker container prune -f ")
    local("docker image  prune -f ")

        
    # Now build the new image
    local("docker build -t {docker_blog_image} .".format(**env))

    # Run the container, exposing port 80
    local("docker run -d -p 80:80 --name {docker_container_name} \
            --restart always  \
            {docker_blog_image} ".format(**env))

def kube_rebuild():
    """Rebuild the pelican site for production and install in a docker image :
       - Kill and remove any existing pelican_site container.
       - Copy the site into the webserver base image, build a new pelican_site
         container.
       - Deploy our new container using Kubernetes
    """
    clean()
    preview()  # Builds the production version of the site

    # Prune stopped containers and dangling old images.
    local("docker container prune -f ")
    local("docker image  prune -f ")

    # Now build the new image # incorporating a version within the  image tag. 
    # Kubernetes likes images to # be tagged in this manner to ease upgrades.
    # bumpbersion is a python package which will increment version flags in
    # files, see .bumpversion.cfg
    # There's got to be aneasier way than this!

    local("bumpversion minor --allow-dirty")
    config = ConfigParser.ConfigParser()
    config.read("version.ini")
    image_version = config.get('vars', 'image_version')

    print('image_version = {}'.format(image_version))
    docker_image_name = "{docker_blog_image}".format(**env) + image_version 

    local("docker build -t {} .".format(docker_image_name))
    local('gcloud docker -- push {}'.format(docker_image_name))

