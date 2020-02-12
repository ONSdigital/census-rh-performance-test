import os

FILE_NAME = os.getenv('FILE_NAME') or './test_data/event_data.txt'
RABBITMQ_URL = os.getenv('RABBITMQ_URL') or 'amqp://guest:guest@localhost:6672/'
EXCHANGE = os.getenv('EXCHANGE') or 'events'
UAC_ROUTING_KEY = os.getenv('UAC_ROUTING_KEY') or 'event.uac.update'
CASE_ROUTING_KEY = os.getenv('CASE_ROUTING_KEY') or 'event.case.update'
DATA_PUBLISH = os.getenv('DATA_PUBLISH') == 'true'

