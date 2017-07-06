Title: Experimenting with running on GKE
Date: 2017-07-05
Category: Tech-Notes
Tags: docker, pelican, GKE, containers, google-container, google-compute

# Moving my blog to run using the Google Container Service.

I'm doing this purely as an experiment to gain experience with using the 
Google container service and Google compute services. The steps required are:

- Establish a google compute account.
- Install the google SDK and gcloud.
- Create a default gcloud configuration.
- Create a  minimum sized cluster to allow us to run Kubernetes and manage our
  blog in a container.
- Upload a container to the Google container repository
- Run said container, this contains a static webpage and an nginx server
- Expose a public IP address for this container.
- Then update necessary DNS records to point the blog to this container.

# Gcloud

I'll be doing the majority of this using the google CLI tool gcloud instead of using the Google cloud dashboard GUI.
Gcloud  being the tool for managing all aspects of google cloud services. It's
installed locally and uses the Google Cloud Platform APIs. It's also what
we'll use to install the Kubernetes cli tool kubectl.

This guide [https://cloud.google.com/sdk/docs/quickstarts] covers the
installation of the SDK under various OSs. I chose to flow the quickstart for
Linux since I'm running Manjaro.

- gcloud requires python 2.7 so I installed the SDK and run the gcloud CLI
  within a virtual environment [https://virtualenv.pypa.io/en/stable/]
```shell
    mkvirtualenv google-cloud -p python2.7
```
- The steps involve downloading a tarfile, untarring  it then running a setup script.
- You've then got the gcloud CLI installed and the guide walks you through
  getting authenticated and some initialization.

Once I installed the SDK and got access to the gcloud CLI the next step was to 
create a 'project'. All services, VMs containers are run within the context of a project. 
```shell
gcloud projects create robren-blog-v1
gcloud projects list
PROJECT_ID       NAME            PROJECT_NUMBER
robren-blog-v1   robren-blog-v1  840355975236
```

Now we update our configuration to use this project by default, to avoid having to
specify the project we're using when running the CLI commands.

```shell
gcloud config set project robren-blog-v1
```

## Always-free tier

Google compute has an "always free" tier. As long as one sticks within
the usage limits outlined in the description here [
https://cloud.google.com/free/] the services will be free.

I'll need to monitor my billing to see if this is indeed the case, but it's
worthwhile  trying to stay in these limits for a tiny experimental blog.

One thing specified in the always-free rules is that we can use 1 f1-micro
instance per month excluding Northern Virginia. So .... I'll want to set my
default region to be a US region that's not in Northern Virginia. The region names and
locations are described here [https://cloud.google.com/compute/docs/regions-zones/regions-zones]


```shell
gcloud config set compute/region us-east1
gcloud config set compute/zone us-east1-c
```

By the time I've configured Kubernetes along with controller nodes etc I know
I'll be in excess of always free limits, but at least I'll get one of the
nodes for free! If I just wanted to run my blog using an nginx server inside
of a compute instance I'd be able to do this with a single micro instance and
no containers, but where would be the fun in that.

# Create a cluster

The container will run within a cluster, this cluster being controlled by
Kubernetes. But first to create the cluster we need to use a gcloud command.
Note the machine type being specified  with the -m flag as f1-micro as well as
the --preemptible flag to keep costs down from the default, but still pretty
cheap machine.

```shell
# Prior to creating the cluster kubectl has to be installed
gcloud components install kubectl

# To see the available options use the built in help
gcloud container clusters create --help

# Create our Cluster
gcloud container clusters create blog-cluster -m f1-micro --num-nodes=3 --disk-size=10 --preemptible

gcloud container clusters create blog-3p-node-cluster -m f1-micro --num-nodes=3 --disk-size=10 --preemptible
Creating cluster blog-3p-node-cluster...done.
Created [https://container.googleapis.com/v1/projects/robren-blog-v1/zones/us-east1-c/clusters/blog-3p-node-cluster].
kubeconfig entry generated for blog-3p-node-cluster.
NAME                  ZONE        MASTER_VERSION  MASTER_IP      MACHINE_TYPE  NODE_VERSION  NUM_NODES  STATUS
blog-3p-node-cluster  us-east1-c  1.6.4           35.185.41.120  f1-micro      1.6.4         3          RUNNING
```

We're forced to use a minimum of 3 nodes for the cluster with the f1-micro
instance. I did find out, by trial and error, that I could use a g1-small
instance with a cluster size of 1 but I'll stick with this more resilient
cluster of 3.

According to the google cost estimator
[https://cloud.google.com/products/calculator/] this should run around $12 per
month, so slightly higher than Digital Ocean but I can live with that. Perhaps
one of the instances will be always-free too!

# Create a container image for my blog

Previous posts describe how I added some custom extensions to the fab file
included with pelican. The readme in [https://github.com/robren/robren-blog]
explains how to install pelican, and use the fabfile to create a docker image. 
Pelican's a bit 'temperamental', my README in github.com/robren/robren-blog has
a few pointers to what I needed to do to get pelican to generate a static
site. If you don't want to get embroiled in learning pelican as well as google
container engine etc, then create some simple content in a subdirectory called
"output" and proceed as  described below as 'build the image"

If docker is not already installed it should be, here's a quick reminder of
what I needed to do. 

## Refresher: Installing docker

Skip if you've already got docker running locally.

This will differ between OS's. For me with Manjaro it was

```shell
sudo pacman -S docker
# Then to make sure docker restarted on reboot
sudo systemctl start docker
sudo systemctl enable  docker
   
# Then to remove the need to run docker with sudo
sudo gpasswd -a $USER docker
newgrp docker # Or log out and back into your system
docker run hello-world
```

## Build the image    

### Create your static html content.

The pelican distribution provides makefiles, fabfiles and a direct pelican
command line to create content in a subdirectory called output. The simplest
way to create the static content would be to directly call

```shell
pelican /path/to/your/content/ 
```
### Create a docker image
The Docker file used is as simple as:

```shell
cat ./Dockerfile
FROM nginx:alpine
COPY output /usr/share/nginx/html
```
Where the static output from Pelican is contained in the output directory

The docker build command is then used to build the image.

```shell
docker build -t alpine-blog 
```

# Upload the  ontainer image to the Google Container Registry

The Google documentation is pretty clear and straightforward on how to do this
[https://cloud.google.com/container-registry/docs/pushing-and-pulling].

Of note are the details of how the docker image must be tagged.

The container image called alpine-blog is the image created by the commands described above, it's 
a lightweight alpine linux, running nginx to host the static site. This is what I want to deploy

```shell
docker images
REPOSITORY          TAG                 IMAGE ID            CREATED             SIZE
alpine-blog         latest              d3c402637e4e        29 minutes ago      20MB
nginx               alpine              a60696d9123b        5 days ago          15.5MB
hello-world         latest              1815c82652c0        2 weeks ago         1.84kB
```
Here's where we tag our image to conform to Google's container repository
requirements as well as push it to the repository.

```shell
docker tag d3c402637e4e gcr.io/robren-blog-v1/alpine-blog
docker images -a
REPOSITORY                          TAG                 IMAGE ID            CREATED             SIZE
alpine-blog                         latest              d3c402637e4e        33 minutes ago      20MB
gcr.io/robren-blog-v1/alpine-blog   latest              d3c402637e4e        33 minutes ago      20MB
nginx                               alpine              a60696d9123b        5 days ago          15.5MB
hello-world                         latest              1815c82652c0        2 weeks ago         1.84kB

gcloud docker -- push gcr.io/robren-blog-v1/alpine-blog
The push refers to a repository [gcr.io/robren-blog-v1/alpine-blog]
1c99d108e437: Preparing
3e2835458dad: Preparing
3da1ee90cad8: Preparing
2ab3866407e2: Preparing
040fd7841192: Preparing

# The first time this is attempted I got an error but an easy to solve link to click and enable the
API from the Cloud console.
denied: Please enable Google Container Registry API in Cloud Console at https://console.cloud.google.com/apis/api/containerregistry.googleapis.com/overview?project=robren-blog-v1 before performing this operation.

# After enabling the API
(google-cloud) ➜  robren-blog git:(master) ✗ gcloud docker -- push gcr.io/robren-blog-v1/alpine-blog
The push refers to a repository [gcr.io/robren-blog-v1/alpine-blog]
1c99d108e437: Pushed
3e2835458dad: Pushed
3da1ee90cad8: Pushed
2ab3866407e2: Pushed
040fd7841192: Layer already exists
latest: digest: sha256:f019e80d59ef82340411ada054987b56b115b6c65f24426f05f34075e6923833 size: 1364
```

## Instruct Kubernetes to run my image.

When we run a container in Kubernetes it turns into something that's abstracted as a "deployment"
```shell
 kubectl run rr-blog --image=gcr.io/robren-blog-v1/alpine-blog --port=80

kubectl get deployments
NAME      DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
rr-blog   1         1         1            1           9h
```
In docker we'd do a docker ps to find the running docker processes. 
In Docker we'd specify the port's to expose to the outside world with parameters passed 
into the docker run command. In Kubernetes we've got to  explicitly "expose" the releeant ports either internally within a cluster or 
externally. 

## Instruct Kubernetes to "deploy" my image

```shell
kubectl expose deployment rr-blog --name rr-blog-deploy --port=80 --target-port=80 --type=LoadBalancer
```

Now the deployment s referred to using another abstraction  "a service". We
can see what external IP has been exposed by using the "get service" command. As
far as I can see I need to expose the deployment using a LoadBalancer to get an
external IP address. The LoadBalancer is an additional cost incurred when
running a service. A necessary component I'm sure when a real world application
has many instances of say a web server which can all be reached via a single
anycast IP address, but perhaps unwanted for our single  test blog.

In software engineering an often quoted aphorism is "Any problem can be solved
with an additional level of abstraction". These abstractions play out and are
necessary when utilizing the full power of Kubernetes as an orchestrator for
containers, e.g using replication controllers, having containers within multiple
domains etc.

The purpose of this experiment was just to get some experience using the gcloud
CLI as well as kubectl and get o sense for how this compares to say docker
machine for a simple container deployment.


```shell
(google-cloud) ➜  robren-blog git:(master) ✗ kubectl get service
rr-blog-deploy
NAME             CLUSTER-IP     EXTERNAL-IP     PORT(S)        AGE
rr-blog-deploy   10.19.253.94   35.185.16.202   80:31741/TCP   52s

```

After updating our DNS records, I use fastmail as my DNS provider,  to point
robren.net to the External-IP

```shell
curl robren.net
<!DOCTYPE html>
<html lang="en" prefix="og: http://ogp.me/ns# fb: https://www.facebook.com/2008/fbml">
<head>
    <title>Rob Rennison's Blog</title>
Snip
```
## Contemplation and next steps

Quite a few moving parts! Clearly overkill for a tiny static site, but
nonetheless a useful exercise in walking through and using gcloud and kubectl.

There's meant to be some good integration with a CI system such as Jenkins
which will make updates to the blog, on github, automatically deploy a new image to google
container registry, that's clearly an area for more experiment and playing.
I've used Jenkins in a test capacity on a python project  and run the unit
tests upon a new git push, but need to understand how to  utilize Jenkins to
build a new container and deploy to GCE.

From a cost perspective this google container service is overkill for a simple
static blog, so I think I'll be moving onto a simpler cheaper solution. I've
heard good things about Vipr.org and will explore them next.

Update to reflect using the yaml file and how to force restarting of the pods






