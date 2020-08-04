# census-rh-performance-test

Code related to the performance testing of RH

## Locust

For details about using Locust for load testing see https://docs.locust.io/en/stable/index.html


### Run - Local

Clone the repository. Change to the census-rh-performance-test directory where the repository was cloned. Run

    $ pipenv shell
    $ locust -f ./locust_tasks/locustfile.py  --host=http://localhost:9092

### Build Docker image and run locally 

To build a new docker image:

    $ docker build --tag loadtest:latest .
    
To run docker locally:

    $ docker run -d -p 5557:5557 -p 5558:5558 -p 8089:8089 -e TARGET_HOST=http://host.docker.internal:9092 -e DATA_PUBLISH=false -e INSTANCE_NUM=1 -e MAX_INSTANCES=1 loadtest

If you want the test code to publish the test data to RH on startup then you'll need to set the RABBITMQ\_URL and DATA\_PUBLISH environment variables: 
 
    $ docker run -d -p 5557:5557 -p 5558:5558 -p 8089:8089 -e TARGET_HOST=http://host.docker.internal:9092 -e RABBITMQ_URL=amqp://guest:guest@host.docker.internal:6672 -e DATA_PUBLISH=true -e INSTANCE_NUM=1 -e MAX_INSTANCES=1 loadtest

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

To build and publish the docker image CATD recommended:

    $ export PROJECT_ID="census-rh-loadgen"
    $ gcp rh loadgen
    $ docker build -t eu.gcr.io/${PROJECT_ID}/locust-tasks .
    $ docker push eu.gcr.io/${PROJECT_ID}/locust-tasks:latest

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


### Run - Local Locust for local RH

It's probably best to use the latest 3.7.x version of Python to locally run Locust. It's known to work on 3.7.5 but the status for earlier versions is unknown.

Before attempting a local run you'll need to create some test data and start the shell:

	$ cd census-rh-performance-test
	$ cp test_data/example_event_data.2.txt test_data/event_data.txt 
	$ pipenv shell

To do a command line run against a local RH:
	
	$ locust -f locust_tasks/locustfile.py --no-web --clients 5 --hatch-rate 1 --csv-full-history --csv /tmp/rhui.csv --reset-stats --host http://localhost:9092 2>&1 | tee /tmp/locust.log

To run in the browser firstly start Locust and then point the browser at the Locust control panel: http://localhost:8089/

	$ locust -f locust_tasks/locustfile.py --host http://localhost:9092

### Run - Local Locust against RH in GCP

As before you'll probably need to be running the latest Python 3.7.x. 

To run a local Locust to generate traffic for a RH which is deployed in GCP then 
you'll need a command like:

    $ locust -f locust_tasks/locustfile.py --no-web --clients 750 --hatch-rate 20 --csv-full-history --csv /tmp/rhui.csv --reset-stats --host=http://34.107.206.101

I've found running, say, 5% of traffic locally a good way to differentiate between genuine errors and spurious errors which are sometimes reported by the GCP Locust.

It's also a good way of quickly testing changes to locustfile.py.

To avoid misleading statistics it's worth doing a '--reset-stats', so that the stats are cleared down when all clients have been hatched.

### Real world Locust comments

Locust is not a performance measurement tool so it's best to only use its timings for guidance. If you want
to know if the site is responsive enough then manually run RH whilst the performance test is running. You'll need 
to be manually judging if the website passes based on a feel for the slowest 10% of transactions.

The usual degradation of RH is:

* RH is super responsive. Pass
* Starts to get just a little slow. No slow outlying transactions observed. Pass.
* Slows down just a little, but still quite acceptable. The odd transaction starts taking a noticeable amount of time. Marginal fail.
* Most interactions too slow. Fail. 
* Site very slow. Intermittent errors. Fail.

To reduce the chances of intermittent Locust problems (browser app hangs or intermittent 
errors reported):

* Run workers with a whole cpu allocation.
* Try not to get workers above about 50% cpu.
* Make sure master has quite a bit of memory headroom. I needed to frequently restart 
Locust before increasing its memory.

If the Locust web app is not responding it can sometimes be saved by going back to its 
entry point (goto the url line and enter return).

Locust may need to be restarted if it:
* reports an unexpectedly high number of errors, which are not happening when running manually or in a control Locust.
* reports high max times which are again just don't seem correct.
* stops responding in the browser.

If Locust needs to be restarted then I don't think there is any shortcut. It's best to 
scaled down the master and the workers before scaling them both back up.


### Other real world testing comments

Avoid taking any measurements of Java processes until the JVM has warmed up. You don't want
to be comparing the times from a jitted VM against another run with a cold JVM. The warmup
takes at least 3 minutes under load, and up to 15 minutes on a fractional cpu.

If there is a short term increase in errors then make sure that a RHSVC instance has not been
restarted (inevitably memory exhausted).

If you are planning to stress one element of the system then you'll want to avoid accidently
running any other part of the system near peak. The easiest way to be sure of this is to do 
an initial calibration run by running the system to some level of significant load. You can
then scale down the service of interest knowing that the rest of the system can comfortably
cope up to that now calibrated level of load.

The timings on the individual endpoints can be helpful for working out if delays are caused 
by RHUI or RHSVC. When examining the impact of changes it can be better to monitor the timings
for the most appropriate endpoint rather than the overall averages.

Locust is driven by the number of simulated users but it can be more helpful to think about the
load based on some appropriate metric, such as number of launches achieved per second/hour. This is 
because: 

* The number of users doesn't really always reflect what the system can realistically achieve. When
the system is under load you can increase the number of users but the number of launches per second 
goes down (as each request by the simulated user is running a bit slower).
* The tasks done by the simulated users will surely change and there is a high chance that delay
between each action taken increases.


### Environment configuration items

There are a number of environment variable configuration items which can be set:

* FILE\_NAME default './test\_data/event\_data.txt' for pre-canned test data
* RABBITMQ\_URL default 'amqp://guest:guest@localhost:6672/'
* EXCHANGE default 'events'
* UAC\_ROUTING\_KEY default 'event.uac.update'
* CASE\_ROUTING\_KEY default 'event.case.update'
* DATA\_PUBLISH default false, whether to publish test data to Firestore
* INSTANCE\_NUM no default. Is the instance number for the current run. The Locust test will read
its own section of the event data file. For example if the event data file has 100 cases and this is 
instance 3 of 4 then it will only read cases 51 to 75 and sequentially use these during testing.
* MAX\_INSTANCES no default. This is the number of workers that will be sharing the event data file. 
