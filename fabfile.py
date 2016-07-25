from fabric.api import *
import fabric.contrib.project as project
import os
import shutil
import sys
import SocketServer

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
env.docker_blog_image = 'nginx-blog'
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
       - Mount our site into the webserver container and run it.

    """
    clean()
    preview()  # Builds the production version of the site

    if local("docker ps -a | grep %s; exit 0" %
             env.docker_container_name, capture=True) != "":
        local("docker rm -f  {docker_container_name}".format(**env))


# Remove the existing blog docker image
    if local("docker images | grep %s; exit 0" %
            env.docker_blog_image, capture=True) != "" :
        local("docker rmi  {docker_blog_image}".format(**env))
        
# Now build and run the new image
    local("docker build -t {docker_blog_image} .".format(**env))

    local("docker run -d -p 80:80 --name {docker_container_name} \
            {docker_blog_image} ".format(**env))

    # Now run the base image and map our site inside the container.
#    abs_site_dir = os.path.abspath('output')
#    local("docker run -d -p 80:80 -v {0}:{docker_target_dir} \
#            --name {docker_container_name} {docker_blog_image} \
#            ".format(abs_site_dir, **env))
