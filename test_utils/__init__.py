"""
Test utilities.

Since pytest discourages putting __init__.py into testdirectory
(i.e. making tests a package) one cannot import from anywhere
under tests folder. However, some utility classes/methods might be useful
in multiple test modules (i.e. factoryboy factories, base test classes).

So this package is the place to put them.
"""
import copy
import json
from unittest import mock
from uuid import uuid4

from django.test import TestCase
from django.test.client import RequestFactory
from edx_rest_framework_extensions.auth.jwt.cookies import jwt_cookie_name
from edx_rest_framework_extensions.auth.jwt.tests.utils import generate_jwt_token, generate_unversioned_payload
from faker import Faker
from pytest import mark
from rest_framework.test import APIClient, APITestCase

from enterprise_access.apps.core.constants import SYSTEM_ENTERPRISE_ADMIN_ROLE
from enterprise_access.apps.core.tests.factories import UserFactory

TEST_USERNAME = 'api_worker'
TEST_EMAIL = 'test@email.com'
TEST_PASSWORD = 'QWERTY'
TEST_COURSE_ID = 'edX+DemoX'
TEST_UUID = 'd2098bfb-2c78-44f1-9eb2-b94475356a3f'
TEST_PARTER_UUID = '32504a3e-7715-48ea-b9cc-ab5a75eb0271'
TEST_PARTNER_NAME = 'edX'
TEST_USER_ID = 1
COURSE_TITLE_ABOUT_PIE = 'How to Bake a Pie: A Slice of Heaven'
COURSE_TITLE_ABOUT_CAKE = 'How to Bake a Cake: So Delicious It Should Be Illegal'
TEST_ENTERPRISE_UUID = uuid4()
TEST_ENTERPRISE_GROUP_UUID = uuid4()
TEST_USER_RECORD = {
    'id': TEST_USER_ID,
    'enterprise_customer': {
        'uuid': str(TEST_ENTERPRISE_UUID),
    },
    'active': True,
    'user_id': 1,
    'user': {
        'id': TEST_USER_ID,
        'username': 'billy_bob',
        'first_name': 'billy',
        'last_name': 'bob',
        'email': 'billy@bobby.com',
        'is_staff': False,
        'is_active': True,
        'date_joined': '2024-02-23T20:18:41Z',
    },
    'groups': [],
    'role_assignments': [
        'enterprise_learner',
        'enterprise_admin',
    ],
    'enterprise_group': [str(TEST_ENTERPRISE_GROUP_UUID)],
}

TEST_USER_RECORD_NO_GROUPS = copy.deepcopy(TEST_USER_RECORD)
TEST_USER_RECORD_NO_GROUPS['enterprise_group'] = []

FAKER = Faker()


def random_content_key():
    """
    Helper to craft a random content key.
    """
    fake_words = [
        FAKER.word() + str(FAKER.random_int())
        for _ in range(3)
    ]
    return 'course-v1:{}+{}+{}'.format(*fake_words)


def random_parent_content_key():
    """
    Helper to craft a random content key.
    """
    fake_words = [
        FAKER.word() + str(FAKER.random_int())
        for _ in range(2)
    ]
    return '{}+{}'.format(*fake_words)


@mark.django_db
class APITest(APITestCase):
    """
    Base class for API Tests.
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = UserFactory(username=TEST_USERNAME, email=TEST_EMAIL, is_active=True, password=TEST_PASSWORD)
        cls.user.save()

        cls.client = APIClient()

    def setUp(self):
        """
        Perform operations common to all tests.
        """
        super().setUp()
        self.client.login(username=TEST_USERNAME, password=TEST_PASSWORD)

    def tearDown(self):
        """
        Perform common tear down operations to all tests.
        """
        # Remove client authentication credentials
        self.client.logout()
        super().tearDown()

    def create_user(self, username=TEST_USERNAME, password=TEST_PASSWORD, is_staff=False, **kwargs):
        """
        Create a test user and set its password.
        """
        self.user = UserFactory(username=username, is_active=True, is_staff=is_staff, **kwargs)
        self.user.set_password(password)
        self.user.save()

    def load_json(self, content):
        """
        Parse content from django Response object.

        Arguments:
            content (bytes | str) : content type id bytes for PY3 and is string for PY2

        Returns:
            dict object containing parsed json from response.content
        """
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        return json.loads(content)

    def get_request_with_jwt_cookie(self, system_wide_role=None, context=None):
        """
        Set jwt token in cookies.
        """
        payload = generate_unversioned_payload(self.user)
        if system_wide_role:
            payload.update({
                'roles': [
                    '{system_wide_role}:{context}'.format(system_wide_role=system_wide_role, context=context)
                ]
            })
        jwt_token = generate_jwt_token(payload)

        request = RequestFactory().get('/')
        request.COOKIES[jwt_cookie_name()] = jwt_token
        return request

    def set_jwt_cookie(self, roles_and_contexts=[]):
        """
        Set jwt token in cookies.
        """
        if not roles_and_contexts:
            roles_and_contexts = [{
                'system_wide_role': SYSTEM_ENTERPRISE_ADMIN_ROLE,
                'context': 'some_context'
            }]

        roles = []

        for role_and_context in roles_and_contexts:
            system_wide_role = role_and_context['system_wide_role']
            context = role_and_context.get('context')
            role_data = '{system_wide_role}'.format(system_wide_role=system_wide_role)
            if context is not None:
                role_data += ':{context}'.format(context=context)

            roles.append(role_data)

        payload = generate_unversioned_payload(self.user)
        payload.update({
            'roles': roles,
            'user_id': self.user.lms_user_id,
        })
        jwt_token = generate_jwt_token(payload)

        self.client.cookies[jwt_cookie_name()] = jwt_token


class APITestWithMocks(APITest):
    """
    API test class with discovery api calls in subsidy_request tasks mocked out.

    We call discovery on every SubsidyRequest object save().
    """
    def setUp(self):
        super().setUp()
        self.disco_patcher = mock.patch('enterprise_access.apps.subsidy_request.tasks.DiscoveryApiClient')
        self.mock_discovery_client = self.disco_patcher.start()
        self.mock_discovery_client().get_course_data.return_value = {
            'title': COURSE_TITLE_ABOUT_PIE,
            'owners': [{'uuid': TEST_PARTER_UUID, 'name': TEST_PARTNER_NAME}],
            "entitlements": [{'mode': 'verified', 'price': '199.00', 'currency': 'USD', 'sku': '3964E13'}]
        }

        self.analytics_patcher = mock.patch('analytics.track')
        self.mock_analytics = self.analytics_patcher.start()

        self.addCleanup(self.disco_patcher.stop)
        self.addCleanup(self.analytics_patcher.stop)


class TestCaseWithMockedDiscoveryApiClient(TestCase):
    """
    Test class with discovery api calls in subsidy_request tasks mocked out.

    We call discovery on every SubsidyRequest object save().
    """
    def setUp(self):
        super().setUp()
        self.disco_patcher = mock.patch('enterprise_access.apps.subsidy_request.tasks.DiscoveryApiClient')
        self.mock_discovery_client = self.disco_patcher.start()
        self.mock_discovery_client().get_course_data.return_value = {
            'title': COURSE_TITLE_ABOUT_CAKE,
            'owners': [{'uuid': TEST_PARTER_UUID, 'name': TEST_PARTNER_NAME}],
        }
