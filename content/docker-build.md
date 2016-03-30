Title: Building a Blog in a Box
Date: 2016-03-30 12:17
Category: Docker

This post notes some of the steps taken  to  create a static site based blog and deploying it
using docker. There are a number of moving parts which are each 
pretty straightforward. 

I chose to use the [pelican](http://blog.getpelican.com/) static site
generator. As a lover of markdown and vim, pelican's support for plain text
markup based content seems to fit how I like to take notes and write.

A static site generator takes a bunch of content and spits out a series of
html pages. These pages are what we'll "serve" using a webserver.

The webserver and associated content are what we're going to package together
and run inside of a Docker container. 

We'll then deploy this container inside of a Digital Ocean so-called droplet (
their name for a Virtual Machine)

This first post will describe creating a container containing everything
needed to run the blog.  Future posts will cover the process of "deploying" to
the cloud and how the actual pelican blog is created.

# Creating the  Docker container

A docker container is the runtime instantiation of a docker image. 
The following is a note on creating a Dockerfile to make a Docker Image. An
image is the thing that is instantiated  and becomes a container with the
**docker run** command. Using an Object Oriented software analogy the image
can be thought of as a class whereas the container is an object. 

## Requirements
The specific container for our pelican blog will need to have:

- nginx or similar running
- The static content copied into it at a place where nginx expects the root of
    the content to be
- Network ports exposed to the "outside world"

All of these criteria can be satisifed using arguments to the **docker run**
command, however it's cleaner and more understandable to encapsulate all of
these Requirements in a Dockerfile. The Dockerfile is then used to create a
docker image, which in turn is used by **docker run**.

## Dockerfiles

The docker image command takes a Dockerfile as an input and uses the
instructions contained within to build an image, a "template" which will be
used for future container creation/instantiation.

### Dockerfile commands : Some basics which are in every dockerfile

- FROM: Which base image to base this image on. Found in every Dockerfile
- RUN: Instructions for what to run inside of the docker file during the
  creation of the image e.g. RUN  apt-get install apache2
- CMD: What to run in the container when we run it. Some of the "base images" already have a CMD specifier
so no CMD statement will be needed in your custom Dockerfile

- COPY: Copy new files or directories from the local file system to the containers filesystem
- EXPOSE: Expose a container port to the network outside of the host

Our blog Dockerfile is trivial, however for more details on each of the
commands used in the example see the [Dockerfile reference](https://docs.docker.com/engine/reference/builder/)

There's a dizzying array of documentation about every aspect of the docker
ecosystem, so sometimes the hard part is to figure out how to navigate this
stuff. That's where simple and concrete examples help to cement things.

### The blog image Dockerfile

    :::bash
    test-lt :: rob/Dropbox/Blog » more Dockerfile
    FROM nginx
    COPY robren-blog/output /usr/share/nginx/html
    EXPOSE 80

The **FROM** command illustrates some of the beauty and ease of the docker ecosystem, the fact
that we can use a preconfigured container **nginx** and then adapt it makes
life really simple. nginx is sufficiently qualified and unique, it refers to
the docker image [nginx](https://hub.docker.com/_/nginx/). If we wanted to or
did not trust this image we could of course start with a say a default ubuntu
image and then install nginx inside of this image. 

For our purposes and with over 10 Million downloads I'm sure this container is
pretty "golden". It's also designated as an offical image so there's some sense
that its been tested. In other ecosystems with a hub or repo of sample images/scripts, Ansible
comes to mind, there's often a large swath of half-baked examples and images
leaving one to frustratingly experiment or give up and create ones own.

Within the public dockerhub repo for each of the images, there's usually a pointer to the Dockerfile from which it 
was made. It's worth looking at these to get a sense of what's going on "under the covers". I notice from the nginx image that it
alreade exposes port 80, so I do not need to do this

The **COPY** command copies the static content generated by pelican, in the output directory,  into the
default place within the docker image where nginx expects to server html content from.

    :::bash
	test-lt :: rob/Dropbox/Blog » more robren-blog/Dockerfile
	FROM nginx
	COPY output /usr/share/nginx/html
	test-lt :: rob/Dropbox/Blog »

	test-lt :: rob/Dropbox/Blog » tree -L 2 -F
	.
	├── pelican-themes/
	│   └── pelican-bootstrap3/
	└── robren-blog/
		├── content/
		├── develop_server.sh*
		├── Dockerfile*
		├── fabfile.py*
		├── fabfile.pyc*
		├── Makefile*
		├── output/
		├── pelicanconf.py*
		├── pelicanconf.pyc*
		└── publishconf.py*

	5 directories, 8 files
	
The **EXPOSE** command instructs docker to expose the container's  port 80 as
port 80 on the host which is running the container. This is a subject for a
longer and more detailed post on the nature of docker networking.

### Build the image

    :::bash
	test-lt :: Dropbox/Blog/robren-blog » time docker build  -t robsblogimage .
	Sending build context to Docker daemon 4.127 MB
	Step 1 : FROM nginx
	---> af4b3d7d5401
	Step 2 : COPY output /usr/share/nginx/html
	---> Using cache
	---> 48bcca22cdbf
	Successfully built 48bcca22cdbf
	docker build -t robsblogimage .  0.08s user 0.01s system 71% cpu 0.128 total

### Run a container based on the image

    :::bash
	test-lt :: Dropbox/Blog/robren-blog » docker run --name robsblog -d -p 80:80 robsblogimage
	ec081fb4193b9630ab1e358ef581e97af27fba6f3396dd71f0f8c987fa2e266c
	test-lt :: Dropbox/Blog/robren-blog » docker ps
	CONTAINER ID        IMAGE               COMMAND                  CREATED             STATUS              PORTS                         NAMES
	ec081fb4193b        robsblogimage       "nginx -g 'daemon off"   4 seconds ago       Up 4 seconds        0.0.0.0:80->80/tcp, 443/tcp   robsblog
	t

### Locally curl the blog 

    :::bash
	test-lt :: ~ » curl localhost | head
	% Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
									Dload  Upload   Total   Spent    Left  Speed
	<!DOCTYPE html>    0    0     0      0      0 --:--:-- --:--:-- --:--:--     0
	<html lang="en" prefix="og: http://ogp.me/ns# fb: https://www.facebook.com/2008/fbml">
	<head>
		<title>Pelican Blog Experiment</title>
		<!-- Using the latest rendering mode for IE -->
		<meta http-equiv="X-UA-Compatible" content="IE=edge">
		<meta charset="utf-8">
		<meta name="viewport" content="width=device-width, initial-scale=1.0">
	... snip

We can also use a browser and see the blog at the address "localhost"
The next post will cover deploying this container to digital ocean.