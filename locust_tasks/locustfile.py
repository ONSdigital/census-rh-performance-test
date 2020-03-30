import sys
import os
import logging
from locust import HttpLocust, TaskSequence, TaskSet, seq_task, between

sys.path.append(os.getcwd())
from locust_tasks.setup import setup, randomly_select_uac

logger = logging.getLogger('performance')


class LaunchEQ(TaskSequence):
    """
    Class to represent a user entering a UAC and launching EQ.
    """

    UAC_START = 'Start Census'
    ERROR_PAGE = 'Sorry, something went wrong'

    def on_start(self):
        self.case = randomly_select_uac()

    # assume all users arrive at the start page
    @seq_task(1)
    def get_uac(self):
        """
        GET Start page
        """
        with self.client.get('/en/start/', catch_response=True) as response:
            if self.UAC_START not in response.text:
                response.failure(f'response status={response.status_code}, content {self.UAC_START} not found')
                if self.ERROR_PAGE in response.text:
                    logger.error(f'response status={response.status_code}, content={self.ERROR_PAGE}')
                else:
                    logger.error(f'response status={response.status_code}, content={response.text}')
                self.interrupt()

    @seq_task(2)
    def post_uac(self):
        """
        POST a valid UAC
        """
        with self.client.post("/en/start/", {"uac": self.case['uac']}, catch_response=True) as response:
            if self.case["addressLine1"] not in response.text:
                response.failure(f'response status={response.status_code}, '
                                 f'content {self.case["addressLine1"]} not found')
                if self.ERROR_PAGE in response.text:
                    logger.error(f'response status={response.status_code}, content={self.ERROR_PAGE}')
                else:
                    logger.error(f'response status={response.status_code}, content={response.text}')
                self.interrupt()

    @seq_task(3)
    def post_address_is_correct(self):
        """
        POST address confirmation
        """
        self.client.post("/en/start/confirm-address/", {"address-check-answer": "Yes"}, allow_redirects=False)


#
# This task sequence simulates a user launching EQ with a corrected address.
# This is virtually the same as 'launch_EQ' except that after entering a UAC
# the user says that their address is not correct and enters a corrected address.
# The address correction exercises different backend code. 
#    
class LaunchEQwithAddressCorrection(TaskSequence):

    # assume all users arrive at the start page
    @seq_task(1)
    def start_page(self):
        response = self.client.get("/en/start/")

        
    @seq_task(2)
    def enter_valid_uac(self):
        response = self.client.post("/en/start/", {
            'uac': setup.randomly_select_uac()
        })


    @seq_task(3)
    def select_address_not_correct(self):
        response = self.client.post("/en/start/address-confirmation", {
            'address-check-answer': 'No'
        }, allow_redirects=False)

    @seq_task(4)
    def correct_address(self):
        response = self.client.post("/en/start/address-edit", {
            'address-line-1': '1 High Street',
            'address-line-2': 'Smithfields',
            'address-line-3': '',
            'address-town': 'Exeter',
            'address-postcode': 'EX'
        }, allow_redirects=False)


#
# This task sequence simulates a user following the 'request a new code' sequence of pages.
# The simulated user steps through the pages one by one. They don't go down any of the 
# correction/error paths as this doesn't trigger any significant server side work.
#
class request_new_code(TaskSequence):

    # All users arrive at the start page
    @seq_task(1)
    def start_page(self):
        response = self.client.get("/en/start/")
        
    @seq_task(2)
    def request_new_access_code(self):
        response = self.client.get("/request-access-code")

    @seq_task(3)
    def select_address(self):
        # This code should arguable select one of the available addresses but running 
        # with a fixed address doesn't seem to affect the success of the test
        response = self.client.post("/request-access-code/select-address", {
            'request-address-select': "{'uprn': '10023122452', 'address': hardcoded_address}"
        })

    @seq_task(4)
    def confirm_address(self):
        response = self.client.post("/request-access-code/confirm-address", {
            'request-address-confirmation': 'yes'
        })

    @seq_task(5)
    def enter_mobile_number(self):
        response = self.client.post("/request-access-code/enter-mobile", {
            'request-mobile-number': '07714 330 933'
        })

    @seq_task(6)
    def confirm_mobile_number(self):
        response = self.client.post("/request-access-code/confirm-mobile", {
            'request-mobile-confirmation': 'yes'
        })

    @seq_task(7)
    def start_for_new_uac(self):
        response = self.client.get("/en/start/")

 
class launch_web_chat(TaskSequence):
    """
    This task sequence simulates a user launching web chat.
    """
    
    def on_start(self):
        self.urls_on_current_page = self.toc_urls = None

    # assume all users arrive at the start page
    @seq_task(1)
    def start_page(self):
        response = self.client.get("/en/start/")
        
    @seq_task(2)
    def start_web_chat(self):
        response = self.client.get("/webchat")

    @seq_task(3)
    def enter_web_chat_query(self):
        response = self.client.post("/webchat", {
            'screen_name': 'Fred Smith',
            'country': 'England',
            'query': 'technical'
        }, allow_redirects=False)


class UserBehavior(TaskSet):
    """
    This class controls the balance of the tasks which simulated users are performing.
    TODO: Adjust to a more representative balance. (Currently set for development)
    """
    
    tasks = {
        LaunchEQ
    }


class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    wait_time = between(2, 10)


    def setup(self):
        setup()

