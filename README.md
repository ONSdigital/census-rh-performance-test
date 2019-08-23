# census-rh-performance-test

Code related to the performance testing of RH

## Locust

For details about using Locust for load testing see https://docs.locust.io/en/stable/index.html


### Locust Installation

Firstly make sure you have python installed. Then install Locust by running:

    python3 -m pip install locustio

I had problems and needed to do:

    $ pip install --upgrade pip
    $ CC=clang pip install greenlet
    $ CC=clang pip install locustio

### Running Locust

A simple command to run with 10 simulated users, who arrive a the rate of 2 per second is:

    $ cd census-rh-performance-test/src/rh-locust
    $ locust -f rh.py --no-web -c 10 -r 2 --run-time=2m
