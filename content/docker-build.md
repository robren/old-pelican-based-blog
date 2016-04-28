Title: Containerising A Blog
Date: 2016-04-27 12:20
Category: Tech-Notes
Tags: docker, pelican

This post notes some of the steps taken to create a static site based blog and
containerising it.  Future posts will deal with numerous ways we can "deploy"
it; using docker, docker-machine and perhaps even CoreOS.  The blog is just an
excuse to have something to 'containerize', 'tis not complex enough to warrant
microservices, and multiple containers but can be a platform for me to discuss
my experiences with these.

I chose to use the [pelican](http://blog.getpelican.com/) static site
generator. As a lover of markdown and vim; pelican's support for plain text
markup based content fits how I like to write.

A static site generator takes a bunch of content and spits out a series of
nicely styled html pages. These pages are what we'll "serve" using a webserver
The webserver and associated content are what we're going to package together
and run inside of a Docker container. 

We'll then deploy this container, described in the next post,  inside of a
Digital Ocean so-called droplet (their name for a Virtual Machine)

This first post will describe creating a container containing everything
needed to run the blog.  Future posts will cover the process of "deploying" to
the cloud and how the actual pelican blog is created.

# The static site

I'm not going to focus on the mechanics of creating the blog per-se but did
find the [quickstart](http://docs.getpelican.com/en/3.6.3/quickstart.html) as well as 
[notionsandnotes](http://www.notionsandnotes.org/tech/web-development/pelican-static-blog-setup.html#moving-to-pelican-bootstrap3-theme-and-other-improvements)
useful for understanding  what to modify  to  style the blog.

Here's a quick summary of what a given blog contains: 

* The content directory contains markdown files for each of the blog entries.

* The pelicanconf.py and publishconf.py contain variables describing the
website url, themes to use  etc.

* The output directory is where after running make or the fabric script the
output html is generated into.

Notice the Dockerfile, the only thing non-traditional about this pelican blog. 

    :::bash
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

# Creating the  Docker Image

We're going to bundle the web server along with associated content into
something which docker calls an *image*. When we run that image, the running
image is said to be a *container*. This  *container* is what will be
running our webserver process and 'serving' the blog. 

An image is the thing
that is instantiated  and becomes a container with the **docker run** command.
Using an Object Oriented software analogy the image can be thought of as a
class whereas the container is an object. 

## Requirements
The specific container for our pelican blog will need to have:

- nginx or similar running
- The static content copied into it at a place where nginx expects the root of
    the content to be
- Network ports exposed to the "outside world"

All of these criteria can be satisifed using arguments to the **docker run**
command, however it's cleaner and more understandable to encapsulate all of
these Requirements in a Dockerfile. The Dockerfile is then used to create a
docker image, which in turn is used by **docker run** with our custom docker
image passed in as a parameter.

## Dockerfiles

The *docker build* command takes a Dockerfile as an input and uses the
instructions contained within to build an image. The image being  a "template" which will be
used for future container creation/instantiation.

### Dockerfile commands : Some common  commands 

The Dockerfile is 'usually' a fairly short text file containing upper case
*commands* along with associated parameters. For example:

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
stuff. That's where simple and concrete examples such as this trivial
*containerise a blog* experiment  help to cement things.

### The Dockerfile for our blog image 

    :::bash
    test-lt :: rob/Dropbox/Blog » more Dockerfile
    FROM nginx
    COPY robren-blog/output /usr/share/nginx/html
    EXPOSE 80

The **FROM** command illustrates some of the beauty and ease of the docker
ecosystem.  The FROM command  specifies a base image to start with for our
custom image. The fact that we can use a preconfigured container **nginx** and
then adapt it makes life really simple. These base images, if public, live on
the [docker hub](https://hub.docker.com/explore/) and are copied to a local
cache. There are caveats about using a more fully qualified image name containing the
registry location username and tag for 'production".  

For our purposes and with over 10 Million downloads I'm sure this nginx
container is pretty "golden". It's also designated as an offical image so
there's some sense that its been tested. In other ecosystems with a hub or
repo of sample images/scripts, we don's always get this warm fuzzy.
Ansible-galaxy comes to mind, there's often a large swath of half-baked examples and images
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
	
The **EXPOSE** command instructs docker to expose the container's  port 80 as
port 80 on the host which is running the container. This is a subject for a
longer and more detailed post on the nature of docker networking.

## Build the image

The [docker build](https://docs.docker.com/v1.8/reference/commandline/build/)
command is used, this defaults to using the Dockerfile within the 
directory specified as the final parameter ( note the . at the end of the
command). For fun I timed this, its pretty snappy!

    :::bash
	test-lt :: Dropbox/Blog/robren-blog » time docker build -t robsblogimage .
	Sending build context to Docker daemon  4.38 MB
	Step 1 : FROM nginx
	latest: Pulling from library/nginx
	efd26ecc9548: Already exists
	a3ed95caeb02: Pull complete
	a48df1751a97: Pull complete
	8ddc2d7beb91: Pull complete
	Digest: sha256:2ca2638e55319b7bc0c7d028209ea69b1368e95b01383e66dfe7e4f43780926d
	Status: Downloaded newer image for nginx:latest
	---> 6f8d099c3adc
	Step 2 : COPY output /usr/share/nginx/html
	---> 169b27ba0e93
	Removing intermediate container d7408e5e7dea
	Successfully built 169b27ba0e93
	docker build -t robsblogimage .  0.06s user 0.02s system 0% cpu 17.212 total

### Run a container based on the image

Now that we have our "bespoke" image we can run it using the ... *docker run* command.

- The -d flag specifies that we run the container in the background (as a daemon) 
- The -p 80:80 tells docker to expose port 80 inside the container as port 80 on our host.

		:::bash
		test-lt :: Dropbox/Blog/robren-blog » docker run --name robsblog -d -p 80:80 robsblogimage
		ec081fb4193b9630ab1e358ef581e97af27fba6f3396dd71f0f8c987fa2e266c
		test-lt :: Dropbox/Blog/robren-blog » docker ps
		CONTAINER ID        IMAGE               COMMAND                  CREATED             STATUS              PORTS                         NAMES
		ec081fb4193b        robsblogimage       "nginx -g 'daemon off"   4 seconds ago       Up 4 seconds        0.0.0.0:80->80/tcp, 443/tcp   robsblog

### Locally curl the blog  as a quick test

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

### Keeping it clean: Easy rebuilding
It's very easy to get into a mess of leftover images and containers. The
pelican code includes a handy fabric file to aid in rebuilding and deploying
the blog to github, to  rackspace etc. I added a
new  docker_rebuild target to the fabfile to allow for easy cleanup and rebuilding of the
docker image file. The complete blog along with the modified fabfile.py can be
found at my [robren-blog](https://github.com/robren/robren-blog)

## Next
The next post will cover deploying this container to digital ocean.
