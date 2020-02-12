import pika
import csv
import datetime
import hashlib

from uuid import uuid4
from random import randrange

from . import FILE_NAME, RABBITMQ_URL, EXCHANGE, UAC_ROUTING_KEY, CASE_ROUTING_KEY, DATA_PUBLISH

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
        parameters = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

    with open(FILE_NAME, 'r') as infile:
        reader = csv.DictReader(infile)
        for line in reader:
            if DATA_PUBLISH:
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
            cases.append(line)

    if DATA_PUBLISH:
        connection.close()


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

