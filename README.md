# census-rh-performance-test

Code related to the performance testing of RH

## Locust

For details about using Locust for load testing see https://docs.locust.io/en/stable/index.html


### Run - Local

Clone the repository. Change to the census-rh-performance-test directory where the repository was cloned. Run

1. pipenv shell
2. locust -f ./locust_tasks/locustfile.py  --host=http://localhost:9092

### Build Docker image and run locally 

docker build -t loadtest .
docker run -d -p 5557:5557 -p 5558:5558 -p 8089:8089 -e TARGET_HOST=http://host.docker.internal:9092 -e RABBITMQ_URL=amqp://guest:guest@host.docker.internal:6672 -e DATA_PUBLISH=true loadtest

This and above Run - Local assumes you have RH UI running on port 9092 with all it's dependencies available:
* RH Service
* Redis
* RabbitMQ

In a browser you can launch the Locust GUI at http://localhost:8089

### Run - Kubernetes
Assumes project and K8 cluster has been created. See Terraform repository.

* gcloud builds submit --tag gcr.io/[PROJECT_ID]/locust-tasks:latest
* kubectl apply -f kubernetes_config/master-deployment.yaml
* kubectl apply -f kubernetes_config/master-service.yaml
* kubectl apply -f kubernetes_config/worker-deployment.yaml

Remove service, deployment.
* kubectl delete svc locust-master
* kubectl delete deployment locust-master
* kubectl delete deployment locust-worker

Remember to remove the k8 cluster to avoid ONS still being charged.


### Environment configuration items

There are a number of environment variable configuration items which can be set:

* FILE_NAME default './test_data/event_data.txt' for pre-canned test data
* RABBITMQ_URL default 'amqp://guest:guest@localhost:6672/'
* EXCHANGE default 'events'
* UAC_ROUTING_KEY default 'event.uac.update'
* CASE_ROUTING_KEY default 'event.case.update'
* DATA_PUBLISH default false, whether to publish test data to Firestore

