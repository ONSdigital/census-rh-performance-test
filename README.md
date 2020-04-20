# census-rh-performance-test

Code related to the performance testing of RH

## Locust

For details about using Locust for load testing see https://docs.locust.io/en/stable/index.html


### Run - Local

Clone the repository. Change to the census-rh-performance-test directory where the repository was cloned. Run

    $ pipenv shell
    $ locust -f ./locust_tasks/locustfile.py  --host=http://localhost:9092

### Build Docker image and run locally 

To build and publish the docker image CATD recommended:

    $ export PROJECT_ID="census-rh-loadgen"
    $ gcp rh loadgen
    $ docker build -t eu.gcr.io/${PROJECT_ID}/locust-tasks .
    $ docker push eu.gcr.io/${PROJECT_ID}/locust-tasks:latest
    
To run docker locally:

    $ docker run -d -p 5557:5557 -p 5558:5558 -p 8089:8089 -e TARGET_HOST=http://host.docker.internal:9092 -e RABBITMQ_URL=amqp://guest:guest@host.docker.internal:6672 -e DATA_PUBLISH=true loadtest

This and above Run - Local assumes you have RH UI running on port 9092 with all it's dependencies available:
* RH Service
* Redis
* RabbitMQ

In a browser you can launch the Locust GUI at http://localhost:8089


### Run - Kubernetes
Assumes project and K8 cluster has been created. See Terraform repository.

Before issuing an Kubertetes commands the following substitutions will be needed:
* PROJECT\_ID - At the time of writing this is 'census-rh-loadgen' for the performance environment.
* TARGET\_HOST - This is the IP of the RH start page. It can be found in the browser by looking at the 'census-rh-performance' environment. Then 'Services & Ingress' -> ingress -> Load balancer IP. eg, 'http://http://34.107.206.101'
* RABBITMQ\_CONNECTION - This is used if you want Locust to populate RH Firestore with test data, otherwise use 'nil'.

To deploy:

    $ gcloud builds submit --tag gcr.io/[PROJECT_ID]/locust-tasks:latest
    $ kubectl apply -f kubernetes_config/master-deployment.yaml
    $ kubectl apply -f kubernetes_config/master-service.yaml
    $ kubectl apply -f kubernetes_config/worker-deployment.yaml

Remove service, deployment.

    $ kubectl delete svc locust-master
    $ kubectl delete deployment locust-master
    $ kubectl delete deployment locust-worker

Once the services have been deployed you should be able to open a browser and go to the Locust master control panel.
You can launch it from the browser by firstly in GCP switching to the census-rh-loadgen environment. They go to 'Services & Ingress -> locust-master' and click on the port 80 external endpoint.

Remember to remove the k8 cluster to avoid ONS still being charged.


### Run - Local Locust against RH in GCP

If you want to run a local Locust to generate traffic for a RH which is deployed in GCP then 
you'll need a command like:

    $ locust -f locust_tasks/locustfile.py --no-web --clients 750 --hatch-rate 20 --csv-full-history --csv /tmp/rhui.csv --reset-stats --host=http://34.107.206.101

I've found running, say, 5% of traffic locally a good way to differentiate between genuine errors and spurious errors which are sometimes reported by the GCP Locust.

It's also a good way of quickly testing changes to locustfile.py.

To avoid misleading statistics it's worth doing a '--reset-stats', so that the stats are cleared down when all clients have been hatched.
    

### Environment configuration items

There are a number of environment variable configuration items which can be set:

* FILE_NAME default './test_data/event_data.txt' for pre-canned test data
* RABBITMQ_URL default 'amqp://guest:guest@localhost:6672/'
* EXCHANGE default 'events'
* UAC_ROUTING_KEY default 'event.uac.update'
* CASE_ROUTING_KEY default 'event.case.update'
* DATA_PUBLISH default false, whether to publish test data to Firestore

