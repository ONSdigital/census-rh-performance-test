#

import random
from locust import HttpLocust, TaskSequence, TaskSet, seq_task, task
from pyquery import PyQuery


# TODO:
# - Add delays to each traversal
# - Accept file with list of valid uac's (Number only)
# - Randomly select uau from list
# - Add invalid uac's?
# - Discuss with Paul if any value in picking address from list
# - Add webchat flow

log_status = False
log_response = False

# TODO: Don't use a single UAC. Read a set from file
fixed_uac = 'w4nwwpphjjptp7fn'


#
# This task sequence simulates a user launching EQ.
# The user enters a UAC, confirms their address is correct and then launches EQ.
#    
class launchEQ(TaskSequence):
    def on_start(self):
        self.urls_on_current_page = self.toc_urls = None

    # assume all users arrive at the start page
    @seq_task(1)
    def start_page(self):
        response = self.client.get("/start/")
        logProgress('EQ.1 start_page', response)
        
    @seq_task(2)
    def enter_valid_uac(self):
        response = self.client.post("/start/", {
            'uac': randomlySelectUAC()
        })
        logProgress('EQ.2 enter_valid_uac', response)

    @seq_task(3)
    def select_address_is_correct(self):
        response = self.client.post("/start/address-confirmation", {
            'address-check-answer': 'Yes'
        }, allow_redirects=False)
        logProgress('EQ.3 select_address_is_correct', response)


#
# This task sequence simulates a user launching EQ with a corrected address.
# This is virtually the same as 'launchEQ' except that aftering entering a UAC
# the user says that their address is not correct and enters a corrected address.
# The address correction exercises different backend code. 
#    
class launchEQWithAddressCorrection(TaskSequence):
    def on_start(self):
        self.urls_on_current_page = self.toc_urls = None

    # assume all users arrive at the start page
    @seq_task(1)
    def start_page(self):
        response = self.client.get("/start/")
        logProgress('EQAC.1 start_page', response)
        
    @seq_task(2)
    def enter_valid_uac(self):
        response = self.client.post("/start/", {
            'uac': randomlySelectUAC()
        })
        logProgress('EQAC.2 enter_valid_uac', response)

    @seq_task(3)
    def select_address_not_correct(self):
        response = self.client.post("/start/address-confirmation", {
            'address-check-answer': 'No'
        }, allow_redirects=False)
        logProgress('EQAC.3 select_address_not_correct', response)

    @seq_task(4)
    def correct_address(self):
        response = self.client.post("/start/address-edit", {
            'address-line-1': '1 High Street',
            'address-line-2': 'Smithfields',
            'address-line-3': '',
            'address-town': 'Exeter',
            'address-postcode': 'EX'
        }, allow_redirects=False)
        logProgress('EQAC.4 correct_address', response)


#
# This task sequence simulates a user following the 'request a new code' sequence of pages.
# The simulated user steps through the pages one by one. They don't go down any of the 
# correction/error paths as this doesn't trigger any significant server side work.
#
class requestNewCode(TaskSequence):
    def on_start(self):
        self.urls_on_current_page = self.toc_urls = None

    # All users arrive at the start page
    @seq_task(1)
    def start_page(self):
        response = self.client.get("/start/")
        logProgress('RNC.1 start_page', response)
        
    @seq_task(2)
    def request_new_access_code(self):
        response = self.client.get("/request-access-code")
        logProgress('RNC.2 request_new_access_code', response)

    @seq_task(3)
    def select_address(self):
        # This code should arguable select one of the available addresses but running 
        # with a fixed address doesn't seem to affect the success of the test
        response = self.client.post("/request-access-code/select-address", {
            'request-address-select': "{'uprn': '10023122451', 'address': '1 Gate Reach, Exeter, EX2 6GA'}"
        })
        logProgress('RNC.3 select_address', response)

    @seq_task(4)
    def confirm_address(self):
        response = self.client.post("/request-access-code/confirm-address", {
            'request-address-confirmation': 'yes'
        })
        logProgress('RNC.4 confirm_address', response)

    @seq_task(5)
    def enter_mobile_number(self):
        response = self.client.post("/request-access-code/enter-mobile", {
            'request-mobile-number': '07714 330 933'
        })
        logProgress('RNC.5 enter_mobile_number', response)

    @seq_task(6)
    def confirm_mobile_number(self):
        response = self.client.post("/request-access-code/confirm-mobile", {
            'request-mobile-confirmation': 'yes'
        })
        logProgress('RNC.6 confirm_mobile_number', response)

    @seq_task(7)
    def start_for_new_uac(self):
        response = self.client.get("/start/")
        logProgress('RNC.7 start_for_new_uac', response)

 
class launch_web_chat(TaskSequence):
    """
    This task sequence simulates a user launching web chat.
    """
    
    def on_start(self):
        self.urls_on_current_page = self.toc_urls = None

    # assume all users arrive at the start page
    @seq_task(1)
    def start_page(self):
        response = self.client.get("/start/")
        logProgress('LWC.1 start_page', response)
        
    @seq_task(2)
    def start_web_chat(self):
        response = self.client.get("/webchat")
        logProgress('LWC.2 start_web_chat', response)

    @seq_task(3)
    def enter_web_chat_query(self):
        response = self.client.post("/webchat", {
            'screen_name': 'Fred Smith',
            'country': 'England',
            'query': 'technical'
        }, allow_redirects=False)
        logProgress('LWC.3 enter_web_chat_query', response)


class MyTaskSet(TaskSet):
    tasks = {
        launchEQ: 10,
        launchEQWithAddressCorrection: 1,
        requestNewCode: 1,
        launch_web_chat: 2
    }


def randomlySelectUAC():
    # TODO: randomly select uac from list of valid ones
    return fixed_uac
    
def logProgress(name, response):
    if log_status == True:
        print ('%s Status: %3d' % (name, response.status_code));
    if log_response == True:
        print ('%s Response: %s' % (name, response.text));


class AwesomeUser(HttpLocust):
    task_set = MyTaskSet
    host = "https://dev-rh.int.census-gcp.onsdigital.uk"

    min_wait = 1000
    max_wait = 5000
