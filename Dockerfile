# Start with a base Python 3.7.2 image
FROM python:3.7.2

# Install pipenv via pip
RUN pip install pipenv

COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock

COPY locust_tasks /locust_tasks
COPY test_data /test_data

COPY locust-run.sh locust-run.sh

# Install dependencies via pipenv
RUN pipenv install --deploy --system

# Expose the required Locust ports
EXPOSE 5557 5558 8089

# Start Locust using LOCUS_OPTS environment variable
ENTRYPOINT ["/bin/bash", "locust-run.sh"]

