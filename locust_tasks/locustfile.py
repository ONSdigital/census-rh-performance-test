import sys
import os
import re
import logging
import time
from enum import Enum
from locust import HttpUser, TaskSet, between, SequentialTaskSet, task, events

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
    START = ('<title>Start census - Census 2021</title>',
             'Start census</h1>',
             'Enter your 16-character access code'
             )
    ADDRESS_CORRECT = ('<title>Is this the correct address? - Census 2021</title>',
                       '<h1 class="question__title">',
                       '<fieldset'
                       )
    EQ_LAUNCHED = ('302: Found',
                   '',
                   ''
                   )
    ERROR = ('<title>Error - Census 2021</title>',
             'id="main-content"',
             '<footer'
             )
    ERROR_502 = ('<title>502 Server Error</title>',
                 '',
                 ''
                 )
    ERROR_GENERIC = ('<h1>Error: Server Error</h1>',
                     '',
                     ''
                     )
    SELECT_ADDRESS = ('<title>Select your address - Census 2021</title>',
                      '<h1 class="question__title">Select your address</h1>',
                      'I cannot find my address')
    SELECT_METHOD = ('<title>How would you like to receive a new access code? - Census 2021</title>',
                     '<h1 class="question__title">How would you like to receive a new household access code?</h1>',
                     'To request a census in a different format or for further help, please')
    ENTER_MOBILE = ('<title>What is your mobile phone number? - Census 2021</title>',
                    '<h1 class="question__title">What is your mobile phone number?</h1>',
                    'Continue')
    CONFIRM_MOBILE = ('<title>Is this mobile phone number correct? - Census 2021</title>',
                      '<h1 class="question__title">Is this mobile phone number correct?</h1>',
                      'Continue')
    ENTER_NAME = ('<title>What is your name? - Census 2021</title>',
                  '<h1 class="question__title">What is your name?</h1>',
                  'Continue')
    CONFIRM_NAME = ('<title>Do you want to send a new access code to this address? - Census 2021</title>',
                    '<h1 class="question__title">Do you want to send a new household access code to this address?</h1>',
                    'Continue')
    CODE_SENT = ('<title>We have sent an access code - Census 2021</title>',
                 '',
                 '')


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


class LaunchEQ(SequentialTaskSet):
    """
    Class to represent a user entering a UAC and launching EQ.
    """

    # assume all users arrive at the start page
    @task
    def get_uac(self):
        """
        GET Start page
        """
        self.case = get_next_case()
        with self.client.get('/en/start/', catch_response=True) as response:
            verify_response('Launch-Start', self, response, 200, Page.START)

    @task
    def post_uac(self):
        """
        POST a valid UAC
        """
        with self.client.post("/en/start/", {"uac": self.case['uac']}, catch_response=True) as response:
            verify_response('Launch-EnterUAC', self, response, 200, Page.ADDRESS_CORRECT, self.case["addressLine1"])
            verify_response('Launch-EnterUAC', self, response, 200, Page.ADDRESS_CORRECT, self.case["postcode"])

    @task
    def post_address_is_correct(self):
        """
        POST address confirmation
        """
        with self.client.post("/en/start/confirm-address/", {"address-check-answer": "Yes"}, allow_redirects=False,
                              catch_response=True) as response:
            verify_response('Launch-ConfirmAddr', self, response, 302, Page.EQ_LAUNCHED)


"""
This sequence simulates a user who mistypes their UAC.
The incorrect UAC is 16 characters long so it will still trigger the call to RHSvc.
"""


class LaunchEQInvalidUAC(SequentialTaskSet):
    """
    Class to represent a user who enters an incorrect UAC.
    """

    # assume all users arrive at the start page
    @task(1)
    def get_uac(self):
        """
        GET Start page
        """
        with self.client.get('/en/start/', catch_response=True) as response:
            verify_response('InvalidUAC-Start', self, response, 200, Page.START)

    @task(2)
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


class LaunchEQwithAddressCorrection(SequentialTaskSet):

    # assume all users arrive at the start page
    @task(1)
    def start_page(self):
        self.case = get_next_case()

        with self.client.get('/en/start/', catch_response=True) as response:
            verify_response('AddrCorrection-Start', self, response, 200, Page.START)

    @task(2)
    def enter_valid_uac(self):
        with self.client.post("/en/start/", {"uac": self.case['uac']}, catch_response=True) as response:
            verify_response('AddrCorrection-EnterUAC', self, response, 200, Page.ADDRESS_CORRECT,
                            self.case["addressLine1"])

    @task(3)
    def select_address_not_correct(self):
        with self.client.post("/en/start/confirm-address/", {'address-check-answer': 'no'}, allow_redirects=False,
                              catch_response=True) as response:
            verify_response('AddrCorrection-ConfirmAddr', self, response, 200, Page.ADDRESS_CORRECT)

    @task(4)
    def correct_address(self):
        response = self.client.post("/en/start/address-edit", {
            'address-line-1': '1 High Street',
            'address-line-2': 'Smithfields',
            'address-line-3': '',
            'address-town': 'Exeter',
            'address-postcode': 'EX'
        }, allow_redirects=False)
        verify_response('AddrCorrection-CorrectAddr', self, response, 200, Page.ADDRESS_CORRECT,
                        'TODO-Get working on latest RH')


"""
This task sequence simulates a user following the 'request a new code' sequence of pages.
The simulated user steps through the pages one by one. They don't go down any of the 
correction/error paths as this doesn't trigger any significant server side work.
"""


class RequestNewCodeSMS(SequentialTaskSet):
    """
    Class to represent a user requesting a new UAC, which is to be sent by SMS.
    """

    @task(1)
    def start_page(self):
        """
        GET Start page
        """
        self.case = get_next_case()
        with self.client.get('/en/start/', catch_response=True) as response:
            verify_response('RequestUacSms-Start', self, response, 200, Page.START)

    @task(2)
    def enter_postcode(self):
        """
        POST postcode
        """
        with self.client.post("/en/requests/access-code/enter-address/", {
            'form-enter-address-postcode': self.case['postcode']
        }, catch_response=True) as response:
            self.address_to_select = extractAddress(response, self.case["uprn"])
            verify_response('RequestUacSms-EnterAddress', self, response, 200, Page.SELECT_ADDRESS,
                            self.case["postcode"])

    @task(3)
    def select_address(self):
        """
        POST uprn and whole address extracted as JSON from the HTML in previous task
        """
        logger.info("Address selected: " + self.address_to_select)
        with self.client.post("/en/requests/access-code/select-address/", {
            'form-select-address': self.address_to_select
        }, catch_response=True) as response:
            verify_response('RequestUacSms-SelectAddress', self, response, 200, Page.ADDRESS_CORRECT, self.case["addressLine1"])

    @task(4)
    def confirm_address(self):
        """
        POST 'yes' to confirm address
        """
        with self.client.post("/en/requests/access-code/confirm-address/", {
            'form-confirm-address': 'yes'
        }, catch_response=True) as response:
            verify_response('RequestUacSms-ConfirmAddress', self, response, 200, Page.SELECT_METHOD, "Text message")

    @task(5)
    def select_method(self):
        """
        POST 'sms' to select text message as method of sending UACs
        """
        with self.client.post("/en/requests/access-code/select-method/", {
            'form-select-method': 'sms'
        }, catch_response=True) as response:
            verify_response('RequestUacSms-SelectMethod', self, response, 200, Page.ENTER_MOBILE)

    @task(6)
    def enter_mobile_number(self):
        """
        POST a mobile number
        """
        with self.client.post("/en/requests/access-code/enter-mobile/", {
            'request-mobile-number': '07714 330 933'
        }, catch_response=True) as response:
            verify_response('RequestUacSms-EnterMobileNumber', self, response, 200, Page.CONFIRM_MOBILE, "933")

    @task(7)
    def confirm_mobile_number(self):
        """
        POST 'yes' to confirm mobile number
        """
        with self.client.post("/en/requests/access-code/confirm-mobile/", {
            'request-mobile-confirmation': 'yes'
        }, catch_response=True) as response:
            verify_response('RequestUacSms-ConfirmMobileNumber', self, response, 200, Page.CODE_SENT)


class RequestNewCodePost(SequentialTaskSet):

    # All users arrive at the start page
    @task(1)
    def start_page(self):
        """
        GET Start page
        """
        self.case = get_next_case()
        with self.client.get('/en/start/', catch_response=True) as response:
            verify_response('RequestUacPost-Start', self, response, 200, Page.START)

    @task(2)
    def enter_postcode(self):
        """
        POST postcode
        """
        with self.client.post("/en/requests/access-code/enter-address/", {
            'form-enter-address-postcode': self.case['postcode']
        }, catch_response=True) as response:
            self.address_to_select = extractAddress(response, self.case["uprn"])
            verify_response('RequestUacPost-EnterAddress', self, response, 200, Page.SELECT_ADDRESS,
                            self.case["postcode"])

    @task(3)
    def select_address(self):
        """
        POST uprn and whole address extracted as JSON from the HTML in previous task
        """
        logger.info("Address selected: " + self.address_to_select)
        with self.client.post("/en/requests/access-code/select-address/", {
            'form-select-address': self.address_to_select
        }, catch_response=True) as response:
            verify_response('RequestUacPost-SelectAddress', self, response, 200, Page.ADDRESS_CORRECT, self.case["addressLine1"])

    @task(4)
    def confirm_address(self):
        """
        POST 'yes' to confirm address
        """
        with self.client.post("/en/requests/access-code/confirm-address/", {
            'form-confirm-address': 'yes'
        }, catch_response=True) as response:
            verify_response('RequestUacPost-ConfirmAddress', self, response, 200, Page.SELECT_METHOD, "Post")

    @task(5)
    def select_method(self):
        """
        POST 'post' to select post as method of sending UACs
        """
        with self.client.post("/en/requests/access-code/select-method/", {
            'form-select-method': 'post'
        }, catch_response=True) as response:
            verify_response('RequestUacPost-SelectMethod', self, response, 200, Page.ENTER_NAME, "")

    @task(6)
    def enter_name(self):
        """
        POST 'John' as first name and 'Smith' as last name of person to send the UAC to
        """
        with self.client.post("/en/requests/access-code/enter-name/", {
            'name_first_name': 'John',
            'name_last_name': 'Smith'
        }, catch_response=True) as response:
            verify_response('RequestUacPost-EnterName', self, response, 200, Page.CONFIRM_NAME,
                            "John Smith<br>")

    @task(7)
    def confirm_name_address(self):
        """
        POST 'yes' to confirm name and address
        """
        with self.client.post("/en/requests/access-code/confirm-name-address/", {
            'request-name-address-confirmation': 'yes'
        }, catch_response=True) as response:
            verify_response('RequestUacPost-ConfirmName', self, response, 200, Page.CODE_SENT, "John Smith")


class LaunchWebChat(SequentialTaskSet):
    """
    This task sequence simulates a user launching web chat.
    """

    def on_start(self):
        self.urls_on_current_page = self.toc_urls = None

    # assume all users arrive at the start page
    @task(1)
    def start_page(self):
        self.client.get("/en/start/")

    @task(2)
    def start_web_chat(self):
        self.client.get("/webchat")

    @task(3)
    def enter_web_chat_query(self):
        self.client.post("/webchat", {
            'screen_name': 'Fred Smith',
            'country': 'England',
            'query': 'technical'
        }, allow_redirects=False)


class WebsiteUser(HttpUser):
    """
    The following task sets should currently work:
    - LaunchEQ
    - RequestNewCodeSMS
    - RequestNewCodePost
    - LaunchWebChat
    And the following are currently broken:
    - LaunchEQInvalidUAC
    - LaunchEQwithAddressCorrection
    """
    tasks = {
        LaunchEQ: 0,
        LaunchEQInvalidUAC: 0,
        LaunchEQwithAddressCorrection: 0,
        RequestNewCodeSMS: 0,
        RequestNewCodePost: 1,
        LaunchWebChat: 0
    }
    wait_time = between(2, 10)


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
    page_extract = extract_key_page_content(id, task, resp, current_page)
    if current_page != expected_page:
        failure_message = f'On wrong page. Expected to be on {expected_page.name} page but am on {current_page.name} page.'
        report_failure(id, resp, task, failure_message, page_extract)

    # Status check
    if expected_status != resp.status_code:
        failure_message = f'Status mismatch. Expected {expected_status} but was {resp.status_code}.'
        report_failure(id, resp, task, failure_message, page_extract)

        # Content verification
    if expected_content:
        # Convert expected apostrophes to HTML equivalent
        if "'" in expected_content:
            expected_content = expected_content.replace("'", "&#39;")
        # Check page content
        if expected_content not in resp.text:
            failure_message = f'{current_page.name} page does not contain expected text ({expected_content}).'
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
    # Note that this sleep does not affect the progress of other tasks
    time.sleep(5.0)

    task.interrupt()


""" 
Identifies the current page based on its content.
It returns a Page enum value if the page can be identified, or fails the test if it cannot.
"""


def identify_page(id, task, resp):
    page_content = resp.text

    for page in Page:
        if page.title in page_content:
            return page

    # Identification failed
    failure_message = f'Failed to identify page. Status={resp.status_code}.'
    report_failure(id, resp, task, failure_message, clean_text(page_content))

"""
Returns the address that corresponds to the uprn. This can then be used to select the correct address from the page.
"""
def extractAddress(resp, uprn):
    page_content = resp.text
    page_extract1 = page_content[page_content.index('id="' + uprn + '"'):]
    page_extract2 = page_extract1[page_extract1.index('value='):page_extract1.index('name=')]
    page_extract2 = page_extract2.rstrip()
    address_to_select = page_extract2[7:-1]
    address_to_select = address_to_select.replace('&#34;', '"')
    logger.info("Address extracted: " + address_to_select)

    return address_to_select

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
    if start < 0 or end < 0:
        failure_message = f'Could not find start/end text on the {current_page.name} page. Offsets found {start},{end}'
        report_failure(id, resp, task, failure_message, clean_text(resp.text))

    return page_extract


"""
Removes blank lines from supplied text
"""


def clean_text(text):
    return re.sub(r'\n\s*\n', '\n', text, flags=re.MULTILINE)


@events.test_start.add_listener
def on_test_start(**kw):
    print("test is starting")
    setup()


@events.test_stop.add_listener
def on_test_stop(**kw):
    print("test is stopping")
