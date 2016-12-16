Title: Deploying the blog using docker-machine
Date: 2016-12-16 21:00
Category: Tech-Notes
Tags: docker,docker-machine, pelican

In the earlier post we got our blog deployed inside of a docker container,
said container running nginx to serve our blog. In this article I'll look at
how we can "deploy" this to _The Cloud!_.

I've previously experimented with creating VMs and setting up a cool docker/
dev environment on them, perhaps I'll blog on this at some time, and this was
what I initially thought I'd use as an environment to host a docker blog
container. 

In that scenario I'd copy the DockerFile and associated blog
content over to the remote VM,
then run 'docker build' to create an image, which I'd then run with 'docker
run'. Of course whenever I changed the blog locally I'd need to have a script
to copy the content and rebuild the docker image remotely, then restart the
blog container.

## Enter docker-machine

Docker-machine is a cli tool which will install and run the docker daemon  on a
remote server setting appropriate environment variables which the locally run
docker client will use. The docker-machine command is used in conjunction with
the existing  docker client commands e.g 'docker run' or 'docker ps'.

With this combination, containers can be run, stopped, killed etc on a remote machine
**as-if** they were being run locally, without the need to explicitly ssh into the
remote machine or copy over source files needed to  build an image. It makes
running remote containers insanely easy.

There  are a couple of one-time commands needed to create the remote VM  and
start the VM.

The docker-machine create command is our one-off for creating a remote VM and
installing the docker daemon on it. This command supports multiple drivers so
that VMs can be created on say virtual box or a remote cloud provider e.g AWS,
Digital Ocean, Azure. This is all nicely documented in the 
<a href="https://docs.docker.com/machine/overview/" target="_blank">docker machine docs</a>.

Before we run the docker-machine command to create a new docker enabled VM, we
need to provide docker with an access token from our cloud provider.

The Token is obtained from, in my case, a Digital Ocean Account. From the homepage under
the API tab there's a 'Your Tokens' menu item  under which you can have a
token generated. This token you save to a local file then export to your
environment.

    :::bash
    test-lt :: Dropbox/Blog/robren-blog » more ~/bin/digital-ocean-env.sh
    export DO_API_TOKEN=AAAABBBBCCCCDDDDEEEEFFFFf4a83e89acb63ea18d54bf94252ce2c6

    test-lt :: Dropbox/Blog/robren-blog 1 » source ~/bin/digital-ocean-env.sh

Now we can run the docker-machine create command using the digitalocean driver
along with our access token

    :::bash
    test-lt :: Dropbox/Blog/robren-blog » docker-machine create --driver \
    digitalocean --digitalocean-access-token $DO_API_TOKEN do-blog

After we've issued this, we get instructions of what command to run to setup
the environment variables which will cause our local docker api calls to
operate on this remote VM. We can get these same instructions at any time by
issuing the docker-machine env command:

    :::bash
	➜  robren-blog git:(master) ✗ docker-machine env do-blog
	export DOCKER_TLS_VERIFY="1"
	export DOCKER_HOST="tcp://104.236.68.97:2376"
	export DOCKER_CERT_PATH="/home/test/.docker/machine/machines/do-blog"
	export DOCKER_MACHINE_NAME="do-blog"
	# Run this command to configure your shell:
	# eval $(docker-machine env do-blog)

So, let's export these magical variables that docker machine has created.

    :::bash
    test-lt :: Dropbox/Blog/robren-blog » eval $(docker-machine env do-blog)

Not  magic but still impressive and cool

## Time to deploy to our remote droplet

One of the first steps in  creating a static pelican site is to run a
pelican-quickstart command. This command asks the user a number of questions
regarding their site and how they want to deploy it. In addition to creating
the basic directory structure for the site and some configuration files, it also
produces a Makefile and a fabfile.py. The fabfile.py is used with the *fab* command. 

I've forked the pelican repo and currently have customized it so that the
quickstart generates a fabfile.py  with options for docker deployment a
docker_rebuild target is implemented. The fabfile.py found in my pelican blog
has this capability and can be found at <a href="https://github.com/robren/robren-blog/" target="_blank">github robren-blog</a>.
 
Assuming that the docker-machine credentials and environment are setup as in
the above manual deployment of the blog, we can use the fabfile to automate the
relevant build steps and simplify managing the various remote containers and
images.

    :::bash
	test-lt :: ~/Blog/robren-blog » time fab docker_rebuild
	[localhost] local: pelican -s publishconf.py
	Done: Processed 2 articles, 0 drafts, 0 pages and 0 hidden pages in 0.35 seconds.
	[localhost] local: docker ps -a | grep pelican_site_container; exit 0
	[localhost] local: docker rm -f  pelican_site_container
	pelican_site_container
	[localhost] local: docker images | grep alpine-blog; exit 0
	[localhost] local: docker rmi  alpine-blog
	Untagged: alpine-blog:latest
	Deleted: sha256:caced172392e49ba4a288c44f613094f4eddf548a9bab7a3c9a24ceee1d775c1
	Deleted: sha256:6f82325d033ded4f36591c392cb9765a44e26299bc0bcadcfb104cb99f93d4cc
	[localhost] local: docker build -t alpine-blog .
	Sending build context to Docker daemon 24.05 MB
	Step 1 : FROM nginx:alpine
	---> d964ab5d0abe
	Step 2 : COPY output /usr/share/nginx/html
	---> 0da48d24481b
	Removing intermediate container 1defa8179f0d
	Successfully built 0da48d24481b
	[localhost] local: docker run -d -p 80:80 --name pelican_site_container             alpine-blog
	9692abc8032a4c3cd5fdcc1045344d15e114889785eb7f548a4106aeafc0a031

	Done.
	fab docker_rebuild  1.00s user 0.20s system 3% cpu 34.811 total

Now our blog is remotely deployed in a container on a digital ocean droplet

    :::bash
	test-lt :: ~/Blog/robren-blog » curl robren.net | head
	% Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
									Dload  Upload   Total   Spent    Left  Speed
	100  7493 <!DOCTYPE html>     0      0      0 --:--:-- --:--:-- --:--:--     0
	<html lang="en" prefix="og: http://ogp.me/ns# fb: https://www.facebook.com/2008/fbml">
	<head>
		<title>Rob Rennison's Blog</title>
 
The fabric command trys to ensure we do not end up with lots of docker "cruft"
on the remote machine by explicitly deleting the existing container and it's
image for ever publish.

More on docker cruft removal later!
