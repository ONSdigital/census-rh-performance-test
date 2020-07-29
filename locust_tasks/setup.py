import pika
import csv
import datetime
import hashlib
import sys

from uuid import uuid4
from random import randrange

from . import FILE_NAME, RABBITMQ_URL, EXCHANGE, UAC_ROUTING_KEY, CASE_ROUTING_KEY, DATA_PUBLISH, INSTANCE_NUM, MAX_INSTANCES

case_ref = 84000000
cases = []


def randomly_select_uac():
    return cases[randrange(len(cases))]


def setup():
    """
    Read CSV file and publish UAC and Case update events to RabbitMQ to seed Firestore with test data if requested.
    """

    global cases

    if DATA_PUBLISH:
        publish_test_data()

    num_event_rows = get_num_event_data_records()
    sys.stdout.write('num lines: %d\n' % num_event_rows)
    (first_record, last_record) = calculate_section_of_event_data_file(num_event_rows)            
    read_event_data(first_record, last_record)


def publish_test_data():
    parameters = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    with open(FILE_NAME, 'r') as infile:
        reader = csv.DictReader(infile)
        for line in reader:
            case_id =  str(uuid4())
            collection_exercise_id = str(uuid4())

            uac_event = uac_event_builder(line, case_id, collection_exercise_id)
            channel.basic_publish(exchange=EXCHANGE,
                                  routing_key=UAC_ROUTING_KEY,
                                  body=uac_event)
            
            case_event = case_event_builder(line, case_id, collection_exercise_id)
            channel.basic_publish(exchange=EXCHANGE,
                                  routing_key=CASE_ROUTING_KEY,
                                  body=case_event)

    connection.close()


def get_num_event_data_records():
    lines = 0
    for line in open(FILE_NAME):
        lines += 1
        
    # Actual number of records is one less due to header line
    return lines - 1

    
def calculate_section_of_event_data_file(number_records):
    # Verify env.variables set
    if INSTANCE_NUM is None:
        sys.exit("ERROR: Environment variable 'INSTANCE_NUM' has not been set")
    if MAX_INSTANCES is None:
        sys.exit("ERROR: Environment variable 'MAX_INSTANCES' has not been set")

    # Convert from strings
    instance_num = int(INSTANCE_NUM)
    max_instances = int(MAX_INSTANCES)
    
    # Sanity check the instance settings
    # PMB TODO

    # Calculate range of file owned by this instance
    records_per_instance = number_records / max_instances
    first_record = int(records_per_instance * (instance_num-1))
    last_record = int(records_per_instance * (instance_num)) -1

    sys.stdout.write('Instance %d/%d: Event range: %d...%d inclusive from %d records\n' % (instance_num, max_instances, first_record, last_record, number_records))

    return (first_record, last_record)
    

def read_event_data(first_record, last_record):
    with open(FILE_NAME, 'r') as infile:
        reader = csv.DictReader(infile)
        line_number = 0
        for line in reader:
            if line_number >= first_record and line_number <= last_record:
                cases.append(line)
            line_number += 1


def uac_event_builder(line, case_id, collection_exercise_id):
    """
    Build UAC event message.
    :param line: CSV data
    :param case_id:
    :param collection_exercise_id:
    :return:  UAC event message
    """
    str_list = []
    str_list.append('{"event": { "type": "UAC_UPDATED", "source": "CASE_SERVICE", "channel": "RM", "dateTime": "')
    str_list.append(datetime.datetime.utcnow().isoformat())
    str_list.append('", "transactionId" : "')
    str_list.append(str(uuid4()))
    str_list.append('" }, "payload" : {"uac" : { "uacHash": "')
    str_list.append(hashlib.sha256(line["uac"].encode()).hexdigest())
    str_list.append('", "active" : ')
    str_list.append(line["active"])
    str_list.append(', "questionnaireId" : "')
    str_list.append(line["questionnaireId"])
    str_list.append('", "caseType" : "')
    str_list.append(line["caseType"])
    str_list.append('", "region" : "')
    str_list.append(line["region"])
    str_list.append('", "caseId" : "')
    str_list.append(case_id)
    str_list.append('", "collectionExerciseId" : "')
    str_list.append(collection_exercise_id)
    str_list.append('"}}}')
    return ''.join(str_list)


def case_event_builder(line, case_id, collection_exercise_id):
    """
    Build Case event message.
    :param line: CSV data
    :param case_id:
    :param collection_exercise_id:
    :return: Case event message
    """
    str_list = []
    str_list.append('{"event": { "type": "CASE_UPDATED", "source": "CASE_SERVICE", "channel": "RM", "dateTime": "')
    str_list.append(datetime.datetime.utcnow().isoformat())
    str_list.append('", "transactionId": "')
    str_list.append(str(uuid4()))
    str_list.append('" }, "payload": {"collectionCase": { "id": "')
    str_list.append(case_id)
    str_list.append('", "caseRef": "')
    str_list.append(str(case_ref + 1))
    str_list.append('", "caseType": "')
    str_list.append(line["caseType"])
    str_list.append('", "survey": "CENSUS", "collectionExerciseId": "')
    str_list.append(collection_exercise_id)
    str_list.append('", "address": { "addressLine1": "')
    str_list.append(line["addressLine1"])
    str_list.append('", "addressLine2": "')
    str_list.append(line["addressLine2"])
    str_list.append('", "addressLine3": "')
    str_list.append(line["addressLine3"])
    str_list.append('", "townName": "')
    str_list.append(line["townName"])
    str_list.append('", "postcode": "')
    str_list.append(line["postcode"])
    str_list.append('", "region": "E", "latitude": "')
    str_list.append(line["latitude"])
    str_list.append('", "longitude": "')
    str_list.append(line["longitude"])
    str_list.append('", "uprn": "')
    str_list.append(line["uprn"])
    str_list.append('", "arid": "ABPXXXXXX010008328509", "addressType": "')
    str_list.append(line["caseType"])
    str_list.append('", "estabType": "Household"')
    str_list.append('}, "contact": { "title": null, "forename": null, "surname": null, "email": null, "telNo": null')
    str_list.append('}, "state": "ACTIONABLE", "actionableFrom": "')
    str_list.append(datetime.datetime.utcnow().isoformat())
    str_list.append('"}}}')
    return ''.join(str_list)

