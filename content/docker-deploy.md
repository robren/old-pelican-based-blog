Title: Deploying the blog
Date: 2016-04-28 21:00
Category: Tech-Notes
Tags: docker,docker-machine, pelican

In the earlier post we got our blog deployed inside of a docker container,
said container running nginx to serve our blog. In this article I'll look at
how we can "deploy" this to _The Cloud!_.

I've previously experimented with creating VMs and setting up a cool docker/
dev environment on them, perhaps I'll blog on this at some time, and this was
what I initially thought I'd use as an environment to host a docker blog
container. 

In this scenario I'd copy the DockerFile and associated blog
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

The Token is obtained fromi, in my case, a Digital Ocean Account, from the homepage under
the API tab there's a 'Your Tokens' menu item  under which you can have a
token generated. This token you save to a local file then export to your
environment.

    test-lt :: Dropbox/Blog/robren-blog » more ~/bin/digital-ocean-env.sh
    export DO_API_TOKEN=AAAABBBBCCCCDDDDEEEEFFFFf4a83e89acb63ea18d54bf94252ce2c6

    test-lt :: Dropbox/Blog/robren-blog 1 » source ~/bin/digital-ocean-env.sh

Now we can run the docker-machine create command using the digitalocean driver
along with our access token

    :::bash
    test-lt :: Dropbox/Blog/robren-blog » docker-machine create --driver \
    digitalocean --digitalocean-access-token $DO_API_TOKEN do-blog

After we've issued this, we get instructions of what command to run to setup
the environemnt variables which will cause our local docker api calls to
operate on this remote VM. We can get these same instructions at any time by
issuing the docker-machine env command:

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

Here I'm using the fabric script with the target docker_rebuild which I
mentioned that I'd added to the basic fabfile. I'll need to fork the penguin
project and issue a pull request to get this into "mainline". For now the fabfile is at 

<a href="https://github.com/robren/robren-blog/" target="_blank">github robren-blog</a>.
 

    :::bash
	test-lt :: Dropbox/Blog/robren-blog » time fab docker_rebuild
	[localhost] local: pelican -s pelicanconf.py
	Done: Processed 2 articles, 0 drafts, 0 pages and 0 hidden pages in 0.44 seconds.
	result = false

	exited

	[localhost] local: docker rm  robsblog
	robsblog
	[localhost] local: docker rmi  robsblogimage
	Untagged: robsblogimage:latest
	Deleted: sha256:0d7ed5c4705b0e97648f6df11a364a425705eeb3fce1b10bc4dab5512d44b7bd
	Deleted: sha256:9a341b52fd73c4d3abf45682094ed50332e65bd1a4ff2dd796d303f8cba7a1bd
	[localhost] local: docker build -t robsblogimage .
	Sending build context to Docker daemon 4.263 MB
	Step 1 : FROM nginx
	---> af4b3d7d5401
	Step 2 : COPY output /usr/share/nginx/html
	---> d1b3d03ccb71
	Removing intermediate container f2b9eb986212
	Successfully built d1b3d03ccb71
	[localhost] local: docker run -d -p 80:80 --name robsblog robsblogimage
	dcc088003b511a19087762bd53ce2008b34f1d4629984368acaed74aa32c3344

	Done.
	fab docker_rebuild  1.10s user 0.14s system 72% cpu 1.707 total

Work In Progress
