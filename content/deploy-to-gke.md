Title: Experimenting with running the blog on Google Container Engine.
Date: 2017-07-05
Modified:2017-07-07
Category: Tech-Notes
Tags: docker, pelican, GKE, containers, google-container, google-compute


I'm doing this purely as an experiment to gain experience with using the 
Google container service and Google compute services. The steps required are loosely:

- Establish a google compute account.
- Install the google SDK and gcloud.
- Create a default gcloud configuration.
- Create a  minimum sized cluster to allow us to run Kubernetes and manage our
  blog in a container.
- Upload my blog container to the Google Container Registry.
- Create a "deployment" to run the container.
- Expose a public IP address for this container.
- Then update necessary DNS records to point the blog to this container.

## Gcloud and kubectl

I'll be doing the majority of this using two CLI tools, gcloud and kubectl.

The gcloud CLI tool is used for managing all aspects of google cloud services. It's
installed locally and uses the Google Cloud Platform APIs. It's also what
we'll use to install the Kubernetes CLI tool kubectl.

The kubectl CLI tool is used for managing Kubernetes. When to use each tool
should become apparent as we proceed.

This [ SDK quickstart](https://cloud.google.com/sdk/docs/quickstarts) guide covers the
installation of the SDK under various OSs. I chose to follow the quickstart for
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
create a 'project'. All services, VMs and containers are run within the context of a project. 

    :::console
    gcloud projects create robren-blog-v1
    gcloud projects list
    PROJECT_ID       NAME            PROJECT_NUMBER
    robren-blog-v1   robren-blog-v1  840355975236

Now we update our configuration to use this project by default, to avoid having to
specify the project we're using when running the CLI commands.

```shell
gcloud config set project robren-blog-v1
```

### Always-free Google Compute Engine tier

Google compute has an "always free" tier. As long as I stick within
the usage limits outlined in the [Always free description]( 
https://cloud.google.com/free/) the services will be free.

I'll need to monitor my billing to see if this is indeed the case, but it's
worthwhile  trying to stay in these limits for a tiny experimental blog.

One thing specified in the always-free rules is that we can use 1 f1-micro
instance per month excluding Northern Virginia. So .... I'll want to set my
default region to be a US region that's not in Northern Virginia. The region names and
locations are described [here] (https://cloud.google.com/compute/docs/regions-zones/regions-zones)

```shell
gcloud config set compute/region us-east1
gcloud config set compute/zone us-east1-c
```
By the time I've configured Kubernetes along with controller nodes etc I know
I'll be in excess of always free limits, but at least I'll get one of the
nodes for free! If I just wanted to run my blog using an nginx server inside
of a compute instance I'd be able to do this with a single micro instance and
no containers, but where would be the fun in that.

## Create a cluster

The container will run within a cluster, this cluster being controlled by
Kubernetes. To create the cluster we need to use a gcloud command.
Note the machine type being specified  with the -m flag as f1-micro as well as
the --preemptible flag to keep costs down from the default, but still pretty
cheap machine.

```shell
# Prior to creating the cluster kubectl has to be installed
gcloud components install kubectl

# To see the available options use the built in help. In fact all of the gcloud and kubectl
# have help available on a per sub command basis, this is very usefull.
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

## Create a container image for my blog

Previous posts [Deploying using docker machine]({filename}/docker-deploy.md)
describe how I added some custom extensions to the fabric file included with
pelican. The readme in [https://github.com/robren/robren-blog] explains how to
install pelican, and use the fabfile to create a docker image.  Pelican's a
bit 'temperamental', my README in github.com/robren/robren-blog has a few
pointers to what I needed to do to get pelican to generate a static site. If
you don't want to get embroiled in learning pelican as well as google
container engine etc, then create some simple content in a subdirectory called
"output" and proceed as  described below as 'build the image"

If docker is not already installed, here's a quick reminder of
what I needed to do. 

### Refresher: Installing docker

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

### Build the image    

#### Create your static html content.

The pelican distribution provides makefiles, fabfiles and a direct pelican
command line to create content in a subdirectory called output. The simplest
way to create the static content would be to directly call:

```shell
pelican /path/to/your/content/ 
```
#### Create a docker image
The Docker file used is a  simple two liner:

```shell
cat ./Dockerfile
FROM nginx:alpine
COPY output /usr/share/nginx/html
```

This specifies that the base linux container image is the nginx image build on
top of the very lightweight linux container called alpine.`The static output
from Pelican is contained in the output directory and is copied into the
defaule place witin the containers file system where nginx expects to serve
html files from.

The next steps of building and tagging the image can all be compined into one,
I'm just splitting them out for clarity. In my [robren-blog github
repo](https://github.com/robren/robren-blog) fabfile.py script I combine these
operations along with versioning the image into one command available as fab
kub_rebuild.

```shell
docker build -t alpine-blog 
```

## Upload the  container image to the Google Container Registry

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
requirements as well as push it to the repository. The container repo
documentation does not mention the need for versioning ags in the image but as
I later found out, to upgrade the images and make containers restart with new
versions, it's best to give an explicit version for, here 0.1.0, for each
image.

```shell
docker tag d3c402637e4e gcr.io/robren-blog-v1/alpine-blog:0.1.0
docker images -a
REPOSITORY                          TAG                 IMAGE ID            CREATED             SIZE
alpine-blog                         latest              d3c402637e4e        33 minutes ago      20MB
gcr.io/robren-blog-v1/alpine-blog   0.1.0               d3c402637e4e        33 minutes ago      20MB
nginx                               alpine              a60696d9123b        5 days ago          15.5MB
hello-world                         latest              1815c82652c0        2 weeks ago         1.84kB
```
Next we need to push the now correctly named image to the google container
service. Note the use of the gcloud docker command not the docker push command
that docker users maybe familiar with.

```shell
gcloud docker -- push gcr.io/robren-blog-v1/alpine-blog:0.1.0
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
(google-cloud) ➜  robren-blog git:(master) ✗ gcloud docker -- push gcr.io/robren-blog-v1/alpine-blog:0.1.0
The push refers to a repository [gcr.io/robren-blog-v1/alpine-blog]
1c99d108e437: Pushed
3e2835458dad: Pushed
3da1ee90cad8: Pushed
2ab3866407e2: Pushed
040fd7841192: Layer already exists
0.1.0: digest: sha256:f019e80d59ef82340411ada054987b56b115b6c65f24426f05f34075e6923833 size: 1364
```
## Instruct Kubernetes to run my image.
So far everything we've done is easily understandable by anyone with even a
small amount of experience in docker, we created images with suitable tags and
uploaded to a google container repo.

Now to run copies of these containers, we've got multiple choices and
multiple new abstractions to learn. Some of these choices are becomming  obsolete,
Kubernetes having evolved a lot in the last few years. I'll cut to the chase
and point out what I interpret as the right way to deploy containers within
Kuberenetes. The current best practice appears to be to use so called deployments, read on.

### Pods
- Pods
    A group of one or more running containers is called a "pod" in Kubernetes
    parlance. Pods can be created and managed directly but it's **not
    recommended**
    
    The following advice is from the [Kubernetes
    documentation](https://kubernetes.io/docs/concepts/workloads/pods/pod/)

```
Pods aren’t intended to be treated as durable entities. They won’t survive
scheduling failures, node failures, or other evictions, such as due to lack of
resources, or in the case of node maintenance.
In general, users shouldn’t need to create pods directly. They should almost
always use controllers (e.g., Deployments), even for singletons. Controllers
provide self-healing with a cluster scope, as well as replication and rollout
management.
```

This beg's the question what's a Deployment?

### Deployments.

Deployments appear to be the "way to go!" They are an abstraction which
provide declarative definitions for how to run Pods ( i.e our desired
containers) and Replica sets (the documentation is particularly unclear here)
```
The Kuberenetes documentation states:
A ReplicaSet ensures that a specified number of pod “replicas” are running at
any given time.
```
Deployments manage updating pods to new versions as well as managing the
containers within the pods to ensure for example that they are restarted if the node they are
living on dies.

We can either create the deployment from the command line, as shown below or,
as a  better practice, specify the parameters for the deployment in a .yaml
file as shown next.

```shell
 kubectl run rr-blog --image=gcr.io/robren-blog-v1/alpine-blog --port=80

kubectl get deployments
NAME      DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
rr-blog   1         1         1            1           9h

```
From now on we'll use the yaml file for specifying how to create the deployment.

```shell
cat deploy.yaml
apiVersion: apps/v1beta1 # for versions before 1.6.0 use extensions/v1beta1
kind: Deployment
metadata:
  name: rr-blog-deploy
spec:
  replicas: 3
  template:
    metadata:
      labels:
        run: rr-blog
    spec:
      containers:
      - name: alpine-blog
        image: gcr.io/robren-blog-v1/alpine-blog:0.29.0
        ports:
        - containerPort: 80
        imagePullPolicy: Always
```
- The name parameters at the top level defines the name of the deployment.
- The replicas parameter defines how many instances of the containers we want
  to run
- The labels parameter containing  the label *run*  and value *rr-blog*  maybe used  as a filter in various _get_ commands.
- The spec section is similar to a docker compose file, specifying where the
  container images come from, what internal port to listen on etc.

```shell
kubectl create -f deploy.yaml
deployment "rr-blog-deploy" created
kubectl get deploy
NAME             DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
rr-blog-deploy   3         3         3            2           4s
```
A few seconds later we go from 2 to 3 available pods

```shell
kubectl get deploy
NAME             DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
rr-blog-deploy   3         3         3            3           7s
```
We can see the individual containers, within pods, be using the *get* command.

```shell
(robren-blog) ➜  robren-blog git:(master) ✗ kubectl get pods
NAME                              READY     STATUS    RESTARTS   AGE
rr-blog-deploy-1503925906-77sc3   1/1       Running   0          11s
rr-blog-deploy-1503925906-bsprz   1/1       Running   0          11s
rr-blog-deploy-1503925906-qfmlg   1/1       Running   0          11s
```
### Expose the webserver to the outside world.

In order to communicate with the pods we've got to  explicitly "expose" the
relevant ports either  to other nodes internally within a cluster or externally. 
For a webserver we'll want to expose port 80. 

```shell
kubectl expose deployment robren-blog-deployment --name rr-blog-deploy --port=80 --target-port=80  --type=LoadBalancer

``` 
After running the kubectl expose command we've created a new object, a
"service"; another abstraction.   As far as I understand from the documents
and experiments, I need to expose the deployment using a _LoadBalancer_ type of
service to get an external IP address. 

We can see what external IP has been exposed by using the "get service" command. 

```shell
(google-cloud) ➜  robren-blog git:(master) ✗ kubectl get service
rr-blog-deploy
NAME             CLUSTER-IP     EXTERNAL-IP     PORT(S)        AGE
rr-blog-deploy   10.19.253.94   35.185.16.202   80:31741/TCP   52s
```

Be aware that, the LoadBalancer is an additional cost incurred when running a service. A necessary component
when a real world application has many instances of say a web server
which can all be reached via a single anycast IP address, but perhaps over the
top for our single  test blog.

After updating our DNS records, I use fastmail as my DNS provider,  to point
robren.net to the External-IP we can then see the blog via a browser, or curl
it to prove it's alive!

```shell
curl robren.net
<!DOCTYPE html>
<html lang="en" prefix="og: http://ogp.me/ns# fb: https://www.facebook.com/2008/fbml">
<head>
    <title>Rob Rennison's Blog</title>
Snip
```

### Updating the blog

Assuming you're using versioned images and have both uploaded a new image as
well as modified the image tag specified within the deploy.yaml file
```shell
cat deploy.yaml
--snip
spec:
      containers:
      - name: alpine-blog
        image: gcr.io/robren-blog-v1/alpine-blog:0.2.0
--snip
```

There are at least two ways of updating the running containers.

#### Service interrupting way

There's a way of updating the blog which is destructive, causing a few seconds
of downtime, handy for development but not recommended for a production  service.
 
```shell
kubectl replace -f deploy.yaml --force
```

#### Rolling updates

Upload a new image  with tag :0.3.0 then update the desired image, in the
deploy.yaml file (or in a new yaml file). This time we use the _kubectl apply_ command to perform a
rolling update whereby individual pods are gradually updated to the new
version.

```shell
kubectl apply -f deploy.yaml --record

$ kubectl describe deployments
Name:                   rr-blog-deploy
Namespace:              default
CreationTimestamp:      Sun, 09 Jul 2017 22:37:21 -0400
Labels:                 run=rr-blog
Annotations:            deployment.kubernetes.io/revision=2
                        kubectl.kubernetes.io/last-applied-configuration={"apiVersion":"apps/v1beta1","kind":"Deployment","metadata":{"annotations":{},"name":"rr-blog-deploy","namespace":"default"},"spec":{"replicas":3,"temp...
                        kubernetes.io/change-cause=kubectl apply --filename=deploy.yaml --record=true
Selector:               run=rr-blog
Replicas:               3 desired | 3 updated | 3 total | 3 available | 0 unavailable
StrategyType:           RollingUpdate
MinReadySeconds:        0
RollingUpdateStrategy:  25% max unavailable, 25% max surge
Pod Template:
  Labels:       run=rr-blog
  Containers:
   alpine-blog:
    Image:              gcr.io/robren-blog-v1/alpine-blog:0.3.0
    Port:               80/TCP
    Environment:        <none>
    Mounts:             <none>
 
---snip
```

## Contemplation and next steps

In software engineering an often quoted aphorism is "Any problem can be solved
with an additional level of abstraction". These abstractions are
necessary in order to utilize the full power of Kubernetes as an orchestrator for
containers, e.g using replication controllers, having containers within multiple
domains etc.

Initially they seem a bit confusing and unclear but that's where struggling
though an example helps to cement the concepts. In retrosepct we can go a long
way by understanding the follwing objects/ abstractions: 

- Pods
- Deployments
- Services.

The purpose of this experiment was to get some experience using the gcloud CLI
as well as kubectl and get o sense for how this compares to say docker machine
for a simple  remote container deployment. If we wanted multiple instances of
our blog using plain docker we'd be  end up using docker swarm so that too
would introduce more abstractions.

Using the Google Container service APIs via gcloud and Kubectl was
surprisingly easy and intuitive once I'd got a handle on the various
abstractions. The help is pretty good too. 

There are quite  a few moving parts! Clearly overkill for a tiny static site,
but the point was to utlize a concrete application, my blog, and see  how to
deploy it using Kubernetes.

Hopefully this has provided an updated view on   how to deploy a simple app,
from which readers can then tackle the documentation and other exmaples in
more depth to deploy more complex multi container applications back end
database containers etc.

From a cost perspective this google container service is overkill for a 
low load static blog, (the load balancer being the major cost), but it's designed to
scale to much larger systems which do require load balancers, multiple domain
resiliancy etc so this is not a criticism. 

I think I'll  keep the blog on GKE for a month or  just to see what the costs
are,  I know it will be more than Digital Ocean just for the LoadBalance
alone. I'll then move it onto be moving onto a simpler cheaper solution. I've
heard good things about Vultr.com and will explore them next. Of course on the
next Platform, it would be too simple to merely run nginx on there! I'll be
looking at either docker-swarm or perhaps installing Kuberentes there too.




