import sys
import os
import re
import logging
from enum import Enum
from locust import HttpLocust, TaskSequence, TaskSet, seq_task, between

sys.path.append(os.getcwd())
from locust_tasks.setup import setup, randomly_select_uac

logger = logging.getLogger('performance')


class Page(Enum):
    START           = ('<title>Start Census - Census 2021</title>', 
    				   'Start Census</h1>',
    				   'Enter the 16 character code'
    				  )
    ADDRESS_CORRECT = ('<title>Is this address correct? - Census 2021</title>',
                       '<h1 class="question__title">',
                       '<fieldset'
                      )
    EQ_LAUNCHED     = ('302: Found',
                       '', 
                       ''
                      )
  
    def __init__(self, title, extract_start, extract_end):
        self.title = title
        self.extract_start = extract_start
        self.extract_end = extract_end
        
        
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
            verify_response('LEQ.1', self, response, 200, Page.START)

    @seq_task(2)
    def post_uac(self):
        """
        POST a valid UAC
        """
        with self.client.post("/en/start/", {"uac": self.case['uac']}, catch_response=True) as response:
            verify_response('LEQ.2', self, response, 200, Page.ADDRESS_CORRECT, self.case["addressLine1"])

    @seq_task(3)
    def post_address_is_correct(self):
        """
        POST address confirmation
        """
        with self.client.post("/en/start/confirm-address/", {"address-check-answer": "Yes"}, allow_redirects=False, catch_response=True) as response:
            verify_response('LEQ.2', self, response, 302, Page.EQ_LAUNCHED)
        	#logger.error(f'POST address confirmation response code={response.status_code}, content="{response.text}"')


class LaunchEQInvalidUAC(TaskSequence):
    """
    Class to represent a user who enters an incorrect UAC.
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
                response.failure(f'Invalid UAC response status={response.status_code}, content {self.UAC_START} not found')
                if self.ERROR_PAGE in response.text:
                    logger.error(f'Invalid UAC response status={response.status_code}, content={self.ERROR_PAGE}')
                else:
                    logger.error(f'Invalid UAC response status={response.status_code}, content={response.text}')
                self.interrupt()

    @seq_task(2)
    def post_uac(self):
        """
        POST a valid UAC
        """
        with self.client.post("/en/start/", {"uac": 'ABCD1234ABCD1234'}, catch_response=True) as response:
            if response.status_code == 401:
                response.success()
            else:
                response.failure(f'Invalid UAC response status={response.status_code}, '
                                 f'content {self.case["addressLine1"]} not found')
                if self.ERROR_PAGE in response.text:
                    logger.error(f'Invalid UAC response status={response.status_code}, content={self.ERROR_PAGE} url="{response.url}" is_redirect="{response.is_redirect}"')
                else:
                    logger.error(f'Invalid UAC response status={response.status_code}, content={response.text} url="{response.url}" is_redirect="{response.is_redirect}"')
                


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
        LaunchEQ: 1,
		LaunchEQInvalidUAC: 0
    }


class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    wait_time = between(1, 2) 


    def setup(self):
        setup()


#
# This function checks that:
#   - The current page is the expected page.
#   - The actual http response status matches the expected status.
#   - Optionally verifies that key content exists on the current page.
#
# In the event of failure it attempts to:
#   - Supply key debugging information, such as step ID & the UAC, to aid with debugging.
#   - For the error log it records the failure message and key content of the current page.
#   - Aborts the current task.
#
def verify_response(id, task, resp, expected_status, expected_page, expected_content=''):
    print ('In verify_response(%s). Expected:%3d actual:%3d expected_page:%s' % (id, expected_status, resp.status_code, expected_page))
    print ('  URL:%s' % (resp.url))
    print ('  status:%d' % (resp.status_code))
    print ('  Expected page title:%s' % (expected_page.title))

    # Sanity check for missing response 
    if (resp.text in (None, '')):
        print("..EMTPY")
        failure_message = 'Status=' + str(resp.status_code) + '. Empty response!'
        report_failure(id, resp, task, failure_message, '')

    # Page check
    current_page = identify_page(id, task, resp, resp.text)
    if (current_page != expected_page):
        print('..WRONG PAGE')
        failure_message = 'On wrong page. Expected to be on ' + expected_page.name + ' but am on ' + current_page.name + '.'
        page_extract = extract_key_page_content(id, task, resp, current_page)
        report_failure(id, resp, task, failure_message, page_extract)        
    
    # Status check
    if (expected_status != resp.status_code):
        print('..STATUS FAILURE')
        failure_message = 'Status mismatch. Expected ' + str(expected_status) + ' but was ' + str(resp.status_code) + '.'
        page_extract = extract_key_page_content(id, task, resp, current_page)
        report_failure(id, resp, task, failure_message, page_extract)        
    
    # Content verification
    if (expected_content not in (None, '')):
        if (expected_content not in resp.text):
            failure_message = current_page.name + ' page does not contain expected text (' + expected_content + ').'
            page_extract = extract_key_page_content(id, task, resp, current_page)
            report_failure(id, resp, task, failure_message, page_extract)
    
    print('Check OK')
    

def report_failure(id, resp, task, failure_message, page_content):
    error_detail = ''
    if (page_content not in (None, '')):
        error_detail = ' Page content >>> ' + page_content + ' <<<'

    resp.failure(f'ID={id} UAC={task.case["uac"]} Status={resp.status_code}: {failure_message}')
    logger.error(f'ID={id} UAC={task.case["uac"]} Status={resp.status_code}: {failure_message}{error_detail}')
    task.interrupt()


def identify_page(id, task, resp, page_content):
    #print('Identify page')
    page_content=resp.text
    #print(page_content)
    
    for page in Page:
        #print(page.title)
        if (page.title in page_content):
            print(f'{id} Identified page: {page.name}')
            return page
 
    # Identification failed
    failure_message = 'Failed to identify page. Status=' + str(resp.status_code) + '.'
    report_failure(id, resp, task, failure_message, clean_text(page_content))
    

def extract_key_page_content(id, task, resp, current_page):
    # Use page content if start/end markers not set for the page
    if (current_page.extract_start in (None, '') or current_page.extract_end in (None, '')):
        return clean_text(resp.text)
        
    # Grab key page content
    start = resp.text.find(current_page.extract_start)
    end = resp.text.find(current_page.extract_end, start)
    extract = resp.text[start:end]
    page_extract = clean_text(extract)
    
    # Fail if page doesn't contain expected start/end text
    if (start < 0 or end <0):
        failure_message = 'Could not find start/end text on the ' + current_page.name + ' page. Offsets found ' + str(start) + ',' + str(end)
        report_failure(id, resp, task, failure_message, clean_text(resp.text))        
    
    return page_extract
    

# Removes blank lines from supplied text    
def clean_text(text):
    return re.sub(r'\n\s*\n', '\n', text, flags=re.MULTILINE)
