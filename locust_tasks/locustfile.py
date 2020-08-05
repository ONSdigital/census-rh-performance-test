import sys
import os
import re
import logging
import time
from enum import Enum
from locust import HttpLocust, TaskSequence, TaskSet, seq_task, between

sys.path.append(os.getcwd())
from locust_tasks.setup import setup, get_next_case

logger = logging.getLogger('performance')


"""
This enum defines the applications pages.

To identify pages each entry must define some 'title' text, which should only appear on that 
particular page.

If the page specifies some text extract_start/end then the text within this range will be
used in the error message to help debug what has gone wrong. 
If the extract start/end is not specified then the whole page will be added to the error message.
""" 
class Page(Enum):
    ERROR           = ('<title>Error - Census 2021</title>',
                       'id="main-content"',
                       '<footer'
                      )
    START           = ('<title>Start census - Census 2021</title>',
                       'Start Census</h1>',
                       'Enter the 16 character code'
    				  )
    ADDRESS_CORRECT = ('<title>Is this the correct address? - Census 2021</title>',
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

        
"""
This sequence is the principle route used to simulate a user:
  - Arrive at start page
  - Enter a valid UAC
  - Confirm address to launch EQ
"""
class LaunchEQ(TaskSequence):
    """
    Class to represent a user entering a UAC and launching EQ.
    """

    # assume all users arrive at the start page
    @seq_task(1)
    def get_uac(self):
        """
        GET Start page
        """
        self.case = get_next_case()

        with self.client.get('/en/start/', catch_response=True) as response:
            verify_response('Launch-Start', self, response, 200, Page.START)

    @seq_task(2)
    def post_uac(self):
        """
        POST a valid UAC
        """
        with self.client.post("/en/start/", {"uac": self.case['uac']}, catch_response=True) as response:
            verify_response('Launch-EnterUAC', self, response, 200, Page.ADDRESS_CORRECT, self.case["addressLine1"])
            verify_response('Launch-EnterUAC', self, response, 200, Page.ADDRESS_CORRECT, self.case["postcode"])

    @seq_task(3)
    def post_address_is_correct(self):
        """
        POST address confirmation
        """
        with self.client.post("/en/start/confirm-address/", {"address-check-answer": "Yes"}, allow_redirects=False, catch_response=True) as response:
            verify_response('Launch-ConfirmAddr', self, response, 302, Page.EQ_LAUNCHED)


"""
This sequence simulates a user who mistypes their UAC.
The incorrect UAC is 16 characters long so it will still trigger the call to RHSvc.
""" 
class LaunchEQInvalidUAC(TaskSequence):
    """
    Class to represent a user who enters an incorrect UAC.
    """

    # assume all users arrive at the start page
    @seq_task(1)
    def get_uac(self):
        """
        GET Start page
        """
        with self.client.get('/en/start/', catch_response=True) as response:
            verify_response('InvalidUAC-Start', self, response, 200, Page.START)

    @seq_task(2)
    def post_uac(self):
        """
        POST an invalid UAC
        """
        with self.client.post("/en/start/", {"uac": 'ABCD1234ABCD1234'}, catch_response=True) as response:
            verify_response('InvalidUAC-EnterUAC', self, response, 401, Page.START, 'Enter a valid code')


"""
This task sequence simulates a user launching EQ with a corrected address.
This is virtually the same as 'launch_EQ' except that after entering a UAC
the user says that their address is not correct and enters a corrected address.
The address correction exercises different backend code. 
"""    
class LaunchEQwithAddressCorrection(TaskSequence):

    # assume all users arrive at the start page
    @seq_task(1)
    def start_page(self):
        self.case = get_next_case()
    
        with self.client.get('/en/start/', catch_response=True) as response:
            verify_response('AddrCorrection-Start', self, response, 200, Page.START)

        
    @seq_task(2)
    def enter_valid_uac(self):
        with self.client.post("/en/start/", {"uac": self.case['uac']}, catch_response=True) as response:
            verify_response('AddrCorrection-EnterUAC', self, response, 200, Page.ADDRESS_CORRECT, self.case["addressLine1"])

    @seq_task(3)
    def select_address_not_correct(self):
        with self.client.post("/en/start/confirm-address/", {'address-check-answer': 'no'}, allow_redirects=False, catch_response=True) as response:
            verify_response('AddrCorrection-ConfirmAddr', self, response, 200, Page.ADDRESS_CORRECT)

    @seq_task(4)
    def correct_address(self):
        response = self.client.post("/en/start/address-edit", {
            'address-line-1': '1 High Street',
            'address-line-2': 'Smithfields',
            'address-line-3': '',
            'address-town': 'Exeter',
            'address-postcode': 'EX'
        }, allow_redirects=False)
        verify_response('AddrCorrection-CorrectAddr', self, response, 200, Page.ADDRESS_CORRECT, 'TODO-Get working on latest RH')


"""
This task sequence simulates a user following the 'request a new code' sequence of pages.
The simulated user steps through the pages one by one. They don't go down any of the 
correction/error paths as this doesn't trigger any significant server side work.
"""
class request_new_code(TaskSequence):

    # All users arrive at the start page
    @seq_task(1)
    def start_page(self):
        self.client.get("/en/start/")
        
    @seq_task(2)
    def request_new_access_code(self):
        self.client.get("/request-access-code")

    @seq_task(3)
    def select_address(self):
        # This code should arguable select one of the available addresses but running 
        # with a fixed address doesn't seem to affect the success of the test
        self.client.post("/request-access-code/select-address", {
            'request-address-select': "{'uprn': '10023122452', 'address': hardcoded_address}"
        })

    @seq_task(4)
    def confirm_address(self):
        self.client.post("/request-access-code/confirm-address", {
            'request-address-confirmation': 'yes'
        })

    @seq_task(5)
    def enter_mobile_number(self):
        self.client.post("/request-access-code/enter-mobile", {
            'request-mobile-number': '07714 330 933'
        })

    @seq_task(6)
    def confirm_mobile_number(self):
        self.client.post("/request-access-code/confirm-mobile", {
            'request-mobile-confirmation': 'yes'
        })

    @seq_task(7)
    def start_for_new_uac(self):
        self.client.get("/en/start/")

 
class launch_web_chat(TaskSequence):
    """
    This task sequence simulates a user launching web chat.
    """
    
    def on_start(self):
        self.urls_on_current_page = self.toc_urls = None

    # assume all users arrive at the start page
    @seq_task(1)
    def start_page(self):
        self.client.get("/en/start/")
        
    @seq_task(2)
    def start_web_chat(self):
        self.client.get("/webchat")

    @seq_task(3)
    def enter_web_chat_query(self):
        self.client.post("/webchat", {
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
        LaunchEQ: 100,
        LaunchEQInvalidUAC: 0,
        LaunchEQwithAddressCorrection: 0,
        request_new_code: 0,
        launch_web_chat: 0
    }


class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    wait_time = between(2, 10)

    def setup(self):
        setup()


"""
This function should be called after each page transition as it aims to aggressively check that:
  - The current page is the expected page.
  - The actual http response status matches the expected status.
  - Optionally verifies that key content exists on the current page.

In the event of failure it:
  - Reports key debugging information, such as step ID & the UAC, to aid with debugging.
  - For the error log it records the failure message and key content of the current page.
  - Aborts the current task.
"""
def verify_response(id, task, resp, expected_status, expected_page, expected_content=''):
    # print ('In verify_response(%s). Expected:%3d actual:%3d expected_page:%s' % (id, expected_status, resp.status_code, expected_page))
    # print ('  URL:%s' % (resp.url))
    # print ('  status:%d' % (resp.status_code))
    # print ('  Expected page title:%s' % (expected_page.title))

    # Sanity check for missing response 
    if not resp.text:
        failure_message = f'Expected to be on the {expected_page.name} page but got an empty response!'
        report_failure(id, resp, task, failure_message, '')

    # Page check
    current_page = identify_page(id, task, resp)
    if current_page != expected_page:
        failure_message = f'On wrong page. Expected to be on {expected_page.name} page but am on {current_page.name} page.'
        page_extract = extract_key_page_content(id, task, resp, current_page)
        report_failure(id, resp, task, failure_message, page_extract)        
    
    # Status check
    if expected_status != resp.status_code:
        failure_message = f'Status mismatch. Expected {expected_status} but was {resp.status_code}.'
        page_extract = extract_key_page_content(id, task, resp, current_page)
        report_failure(id, resp, task, failure_message, page_extract)        
    
    # Content verification
    if expected_content:
        # Convert expected apostrophes to HTML equivalent
        if "'" in expected_content:
            expected_content = expected_content.replace("'", "&#39;")
        # Check page content
        if expected_content not in resp.text:
            failure_message = f'{current_page.name} page does not contain expected text ({expected_content}).'
            page_extract = extract_key_page_content(id, task, resp, current_page)
            report_failure(id, resp, task, failure_message, page_extract)
    
    resp.success()

    
"""
Reports a test failure:
  - the error is reported to Locust
  - an error is logged with either whole or partial page content
"""
def report_failure(id, resp, task, failure_message, page_content):
    error_detail = ''
    if page_content:
        error_detail = f' Page content >>> {page_content} <<<'

    resp.failure(f'ID={id} UAC={task.case["uac"]} Status={resp.status_code}: {failure_message}')
    logger.error(f'ID={id} UAC={task.case["uac"]} Status={resp.status_code}: {failure_message}{error_detail}')
    
    # Slow down error reporting when things are going wrong (otherwise hundreds of errors are logged in just a few seconds)
    time.sleep(5.0)
    
    task.interrupt()


""" 
Identifies the current page based on its content.
It returns a Page enum value if the page can be identified, or fails the test if it cannot.
"""
def identify_page(id, task, resp):
    page_content=resp.text
    
    for page in Page:
        if page.title in page_content:
            return page

    # Identification failed
    failure_message = f'Failed to identify page. Status={resp.status_code}.'
    report_failure(id, resp, task, failure_message, clean_text(page_content))
    
"""
Returns the key content for the current page.
If the enum data for the current_page doesn't have start and end markers set then
the whole page content is returned.
Excess blank lines are removed to help condense the output.
"""
def extract_key_page_content(id, task, resp, current_page):
    # Use page content if start/end markers not set for the page
    if (not current_page.extract_start) or (not current_page.extract_end):
        return clean_text(resp.text)
        
    # Grab key page content
    start = resp.text.find(current_page.extract_start)
    end = resp.text.find(current_page.extract_end, start)
    extract = resp.text[start:end]
    page_extract = clean_text(extract)
    
    # Fail if page doesn't contain expected start/end text
    if start < 0 or end <0:
        failure_message = f'Could not find start/end text on the {current_page.name} page. Offsets found {start},{end}'
        report_failure(id, resp, task, failure_message, clean_text(resp.text))        
    
    return page_extract
    

"""
Removes blank lines from supplied text
"""
def clean_text(text):
    return re.sub(r'\n\s*\n', '\n', text, flags=re.MULTILINE)
