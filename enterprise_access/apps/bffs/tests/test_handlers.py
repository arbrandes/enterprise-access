"""
Tests for BFF handlers
"""
from unittest import mock

from rest_framework import status

from enterprise_access.apps.bffs.context import HandlerContext
from enterprise_access.apps.bffs.handlers import BaseHandler, BaseLearnerPortalHandler, DashboardHandler
from enterprise_access.apps.bffs.tests.utils import TestHandlerContextMixin


class TestBaseHandler(TestHandlerContextMixin):
    """
    Test BaseHandler
    """

    @mock.patch('enterprise_access.apps.api_client.lms_client.LmsUserApiClient.get_enterprise_customers_for_user')
    def test_base_handler_load_and_process_not_implemented(self, mock_get_enterprise_customers_for_user):
        mock_get_enterprise_customers_for_user.return_value = self.mock_enterprise_learner_response_data
        context = HandlerContext(self.request)
        base_handler = BaseHandler(context)
        with self.assertRaises(NotImplementedError):
            base_handler.load_and_process()

    @mock.patch('enterprise_access.apps.api_client.lms_client.LmsUserApiClient.get_enterprise_customers_for_user')
    def test_base_handler_add_error(self, mock_get_enterprise_customers_for_user):
        mock_get_enterprise_customers_for_user.return_value = self.mock_enterprise_learner_response_data
        context = HandlerContext(self.request)
        base_handler = BaseHandler(context)
        # Define kwargs for add_error
        arguments = {
            **self.mock_error,
            "status_code": status.HTTP_400_BAD_REQUEST
        }
        base_handler.add_error(**arguments)
        self.assertEqual(self.mock_error, base_handler.context.errors[-1])
        self.assertEqual(status.HTTP_400_BAD_REQUEST, base_handler.context.status_code)

    @mock.patch('enterprise_access.apps.api_client.lms_client.LmsUserApiClient.get_enterprise_customers_for_user')
    def test_base_handler_add_warning(self, mock_get_enterprise_customers_for_user):
        mock_get_enterprise_customers_for_user.return_value = self.mock_enterprise_learner_response_data
        context = HandlerContext(self.request)
        base_handler = BaseHandler(context)
        base_handler.add_warning(**self.mock_warning)
        self.assertEqual(self.mock_warning, base_handler.context.warnings[0])


class TestBaseLearnerPortalHandler(TestHandlerContextMixin):
    """
    Test BaseLearnerPortalHandler
    """

    def setUp(self):
        super().setUp()
        self.expected_enterprise_customer = {
            **self.mock_enterprise_customer,
            'disable_search': False,
            'show_integration_warning': True,
        }
        self.expected_enterprise_customer_2 = {
            **self.mock_enterprise_customer_2,
            'disable_search': False,
            'show_integration_warning': False,
        }
        self.mock_subscription_licenses_data = {
            'customer_agreement': None,
            'results': [],
        }
        self.mock_default_enterprise_enrollment_intentions_learner_status_data = {
            "lms_user_id": self.mock_user.id,
            "user_email": self.mock_user.email,
            "enterprise_customer_uuid": self.mock_enterprise_customer_uuid,
            "enrollment_statuses": {
                "needs_enrollment": {
                    "enrollable": [],
                    "not_enrollable": [],
                },
                'already_enrolled': [],
            },
            "metadata": {
                "total_default_enterprise_enrollment_intentions": 0,
                "total_needs_enrollment": {
                    "enrollable": 0,
                    "not_enrollable": 0
                },
                "total_already_enrolled": 0
            }
        }

    def get_expected_enterprise_customer(self, enterprise_customer_user):
        enterprise_customer = enterprise_customer_user.get('enterprise_customer')
        return (
            self.expected_enterprise_customer
            if enterprise_customer.get('uuid') == self.mock_enterprise_customer_uuid
            else self.expected_enterprise_customer_2
        )

    @mock.patch('enterprise_access.apps.api_client.lms_client.LmsUserApiClient.get_enterprise_customers_for_user')
    @mock.patch(
        'enterprise_access.apps.api_client.license_manager_client.LicenseManagerUserApiClient'
        '.get_subscription_licenses_for_learner'
    )
    @mock.patch(
        'enterprise_access.apps.api_client.lms_client.LmsUserApiClient'
        '.get_default_enterprise_enrollment_intentions_learner_status'
    )
    def test_load_and_process(
        self,
        mock_get_default_enrollment_intentions_learner_status,
        mock_get_subscription_licenses_for_learner,
        mock_get_enterprise_customers_for_user,
    ):
        """
        Test load_and_process method
        """
        mock_get_enterprise_customers_for_user.return_value = self.mock_enterprise_learner_response_data
        mock_get_subscription_licenses_for_learner.return_value = self.mock_subscription_licenses_data
        mock_get_default_enrollment_intentions_learner_status.return_value =\
            self.mock_default_enterprise_enrollment_intentions_learner_status_data

        context = HandlerContext(self.request)
        handler = BaseLearnerPortalHandler(context)

        handler.load_and_process()

        # Enterprise Customer related assertions
        actual_enterprise_customer = handler.context.data.get('enterprise_customer')
        actual_active_enterprise_customer = handler.context.data.get('active_enterprise_customer')
        actual_linked_ecus = handler.context.data.get('all_linked_enterprise_customer_users')
        expected_linked_ecus = [
            {
                **enterprise_customer_user,
                'enterprise_customer': self.get_expected_enterprise_customer(enterprise_customer_user),
            }
            for enterprise_customer_user in self.mock_enterprise_learner_response_data['results']
        ]
        actual_staff_enterprise_customer = handler.context.data.get('staff_enterprise_customer')
        expected_staff_enterprise_customer = None
        self.assertEqual(actual_enterprise_customer, self.expected_enterprise_customer)
        self.assertEqual(actual_active_enterprise_customer, self.expected_enterprise_customer)
        self.assertEqual(actual_linked_ecus, expected_linked_ecus)
        self.assertEqual(actual_staff_enterprise_customer, expected_staff_enterprise_customer)

        # Base subscriptions related assertions
        actual_subscriptions = handler.context.data['enterprise_customer_user_subsidies']['subscriptions']
        expected_subscriptions = {
            'customer_agreement': None,
            'subscription_licenses': [],
            'subscription_licenses_by_status': {},
            'subscription_license': None,
            'subscription_plan': None,
            'show_expiration_notifications': False,
        }
        self.assertEqual(actual_subscriptions, expected_subscriptions)

        # Default enterprise enrollment intentions related assertions
        actual_default_enterprise_enrollment_intentions = (
            handler.context.data.get('default_enterprise_enrollment_intentions')
        )
        expected_default_enterprise_enrollment_intentions = (
            self.mock_default_enterprise_enrollment_intentions_learner_status_data
        )
        self.assertEqual(
            actual_default_enterprise_enrollment_intentions,
            expected_default_enterprise_enrollment_intentions
        )

    @mock.patch('enterprise_access.apps.api_client.lms_client.LmsUserApiClient.get_enterprise_customers_for_user')
    def test_load_and_process_without_learner_portal_enabled(self, mock_get_enterprise_customers_for_user):
        """
        Test load_and_process method without learner portal enabled. No enterprise
        customer metadata should be returned.
        """
        mock_customer_without_learner_portal = {
            **self.mock_enterprise_customer,
            'enable_learner_portal': False,
        }
        mock_get_enterprise_customers_for_user.return_value = {
            **self.mock_enterprise_learner_response_data,
            'results': [
                {
                    'active': True,
                    'enterprise_customer': mock_customer_without_learner_portal,
                },
                {
                    'active': False,
                    'enterprise_customer': self.mock_enterprise_customer_2,
                },
            ],
        }
        context = HandlerContext(self.request)
        handler = BaseLearnerPortalHandler(context)

        handler.load_and_process()

        actual_enterprise_customer = handler.context.data.get('enterprise_customer')
        actual_active_enterprise_customer = handler.context.data.get('active_enterprise_customer')
        actual_linked_ecus = handler.context.data.get('all_linked_enterprise_customer_users')

        # Assert enterprise_customer and active_enterprise_customer are None
        self.assertEqual(actual_enterprise_customer, None)
        self.assertEqual(actual_active_enterprise_customer, None)

        # Assert only the enterprise customer with learner portal enabled is returned
        self.assertEqual(len(actual_linked_ecus), 1)
        self.assertEqual(actual_linked_ecus[0]['enterprise_customer'], self.expected_enterprise_customer_2)

        # Assert warnings added for enterprise customers without learner portal enabled
        self.assertEqual(len(handler.context.warnings), 2)
        expected_warning_user_message = 'Learner portal not enabled for enterprise customer'

        def _expected_warning_developer_message(customer_record_key):
            return (
                f"[{customer_record_key}] Learner portal not enabled for enterprise customer "
                f"{mock_customer_without_learner_portal.get('uuid')} for request user {self.mock_user.lms_user_id}"
            )

        self.assertEqual(handler.context.warnings[0]['user_message'], expected_warning_user_message)
        self.assertEqual(
            handler.context.warnings[0]['developer_message'],
            _expected_warning_developer_message(customer_record_key='enterprise_customer')
        )
        self.assertEqual(handler.context.warnings[1]['user_message'], expected_warning_user_message)
        self.assertEqual(
            handler.context.warnings[1]['developer_message'],
            _expected_warning_developer_message(customer_record_key='active_enterprise_customer')
        )

    @mock.patch('enterprise_access.apps.api_client.lms_client.LmsUserApiClient.get_enterprise_customers_for_user')
    @mock.patch('enterprise_access.apps.api_client.lms_client.LmsApiClient.get_enterprise_customer_data')
    def test_load_and_process_staff_enterprise_customer(
        self,
        mock_get_enterprise_customer_data,
        mock_get_enterprise_customers_for_user,
    ):
        mock_get_enterprise_customers_for_user.return_value = {
            **self.mock_enterprise_learner_response_data,
            'results': [],
        }
        mock_get_enterprise_customer_data.return_value = self.mock_enterprise_customer
        request = self.request
        request.user = self.mock_staff_user
        context = HandlerContext(request)
        handler = BaseLearnerPortalHandler(context)

        handler.load_and_process()

        actual_enterprise_customer = handler.context.data.get('enterprise_customer')
        expected_enterprise_customer = self.expected_enterprise_customer
        self.assertEqual(actual_enterprise_customer, expected_enterprise_customer)
        actual_staff_enterprise_customer = handler.context.data.get('staff_enterprise_customer')
        expected_staff_enterprise_customer = self.expected_enterprise_customer
        self.assertEqual(actual_staff_enterprise_customer, expected_staff_enterprise_customer)

    @mock.patch(
        'enterprise_access.apps.api_client.enterprise_catalog_client'
        '.EnterpriseCatalogUserV1ApiClient.get_secured_algolia_api_key'
    )
    @mock.patch('enterprise_access.apps.api_client.lms_client.LmsUserApiClient.get_enterprise_customers_for_user')
    @mock.patch('enterprise_access.apps.api_client.lms_client.LmsApiClient.bulk_enroll_enterprise_learners')
    def test_request_default_enrollment_realizations(
        self,
        mock_bulk_enroll,
        mock_get_customers,
        mock_get_secured_algolia_api_key_for_user,
    ):
        mock_get_customers.return_value = self.mock_enterprise_learner_response_data
        mock_get_secured_algolia_api_key_for_user.return_value = self.mock_secured_algolia_api_key_response
        license_uuids_by_course_run_key = {
            'course-run-1': 'license-1',
            'course-run-2': 'license-2',
        }
        context = HandlerContext(self.request)
        handler = BaseLearnerPortalHandler(context)

        response = handler._request_default_enrollment_realizations(license_uuids_by_course_run_key)

        self.assertEqual(response, mock_bulk_enroll.return_value)
        actual_customer_uuid_arg, actual_payload_arg = mock_bulk_enroll.call_args_list[0][0]
        self.assertEqual(actual_customer_uuid_arg, context.enterprise_customer_uuid)
        expected_payload = [
            {'user_id': context.lms_user_id, 'course_run_key': 'course-run-1',
             'license_uuid': 'license-1', 'is_default_auto_enrollment': True},
            {'user_id': context.lms_user_id, 'course_run_key': 'course-run-2',
             'license_uuid': 'license-2', 'is_default_auto_enrollment': True},
        ]
        self.assertCountEqual(expected_payload, actual_payload_arg)
        self.assertEqual(context.errors, [])

    @mock.patch(
        'enterprise_access.apps.api_client.enterprise_catalog_client'
        '.EnterpriseCatalogUserV1ApiClient.get_secured_algolia_api_key'
    )
    @mock.patch('enterprise_access.apps.api_client.lms_client.LmsUserApiClient.get_enterprise_customers_for_user')
    @mock.patch('enterprise_access.apps.api_client.lms_client.LmsApiClient.bulk_enroll_enterprise_learners')
    def test_request_default_enrollment_realizations_exception(
        self,
        mock_bulk_enroll,
        mock_get_customers,
        mock_get_secured_algolia_api_key_for_user
    ):
        mock_get_customers.return_value = self.mock_enterprise_learner_response_data
        mock_get_secured_algolia_api_key_for_user.return_value = self.mock_secured_algolia_api_key_response
        license_uuids_by_course_run_key = {
            'course-run-1': 'license-1',
            'course-run-2': 'license-2',
        }
        context = HandlerContext(self.request)
        handler = BaseLearnerPortalHandler(context)
        mock_bulk_enroll.side_effect = Exception('foobar')

        response = handler._request_default_enrollment_realizations(license_uuids_by_course_run_key)

        self.assertEqual(response, {})
        self.assertEqual(
            context.errors,
            [{
                'developer_message': 'Default realization enrollment exception: foobar',
                'user_message': 'There was an exception realizing default enrollments',
            }],
        )

    @mock.patch(
        'enterprise_access.apps.api_client.enterprise_catalog_client'
        '.EnterpriseCatalogUserV1ApiClient.get_secured_algolia_api_key'
    )
    @mock.patch(
        'enterprise_access.apps.api_client.lms_client.LmsUserApiClient'
        '.get_enterprise_customers_for_user')
    @mock.patch(
        'enterprise_access.apps.api_client.lms_client.LmsApiClient'
        '.bulk_enroll_enterprise_learners')
    @mock.patch(
        'enterprise_access.apps.api_client.lms_client.LmsUserApiClient'
        '.get_default_enterprise_enrollment_intentions_learner_status'
    )
    def test_realize_default_enrollments(
        self, mock_get_intentions, mock_bulk_enroll, mock_get_customers, mock_get_secured_algolia_api_key_for_user
    ):
        mock_get_customers.return_value = self.mock_enterprise_learner_response_data
        mock_get_secured_algolia_api_key_for_user.return_value = self.mock_secured_algolia_api_key_response
        mock_get_intentions.return_value = {
            "lms_user_id": self.mock_user.id,
            "user_email": self.mock_user.email,
            "enterprise_customer_uuid": self.mock_enterprise_customer_uuid,
            "enrollment_statuses": {
                "needs_enrollment": {
                    "enrollable": [
                        {
                            'applicable_enterprise_catalog_uuids': ['catalog-55', 'catalog-1'],
                            'course_run_key': 'course-run-1',
                        },
                        {
                            'applicable_enterprise_catalog_uuids': ['catalog-88', 'catalog-1'],
                            'course_run_key': 'course-run-2',
                        },
                    ],
                    "not_enrollable": [],
                },
                'already_enrolled': [],
            },
        }
        mock_bulk_enroll.return_value = {
            'successes': [
                {'course_run_key': 'course-run-1'},
            ],
            'failures': [
                {'course_run_key': 'course-run-2'},
            ],
        }

        context = HandlerContext(self.request)
        context.data['enterprise_customer_user_subsidies'] = {
            'subscriptions': {
                'subscription_licenses_by_status': {
                    'activated': [{
                        'uuid': 'license-1',
                        'subscription_plan': {
                            'is_current': True,
                            'uuid': 'subscription-plan-1',
                            'enterprise_catalog_uuid': 'catalog-1',
                        },
                    }]
                }
            }
        }
        handler = BaseLearnerPortalHandler(context)

        handler.load_default_enterprise_enrollment_intentions()
        handler.enroll_in_redeemable_default_enterprise_enrollment_intentions()

        actual_customer_uuid_arg, actual_payload_arg = mock_bulk_enroll.call_args_list[0][0]
        self.assertEqual(actual_customer_uuid_arg, context.enterprise_customer_uuid)
        expected_payload = [
            {'user_id': context.lms_user_id, 'course_run_key': 'course-run-1',
             'license_uuid': 'license-1', 'is_default_auto_enrollment': True},
            {'user_id': context.lms_user_id, 'course_run_key': 'course-run-2',
             'license_uuid': 'license-1', 'is_default_auto_enrollment': True},
        ]
        self.assertCountEqual(expected_payload, actual_payload_arg)
        self.assertEqual(
            handler.context.data['default_enterprise_enrollment_realizations'],
            [{
                'course_key': 'course-run-1',
                'enrollment_status': 'enrolled',
                'subscription_license_uuid': 'license-1',
            }],
        )
        self.assertEqual(
            handler.context.errors,
            [{
                'developer_message': (
                    'Default realization enrollment failures: [{"course_run_key": "course-run-2"}]'
                ),
                'user_message': 'There were failures realizing default enrollments',
            }],
        )

        # a simple validation here that a second consecutive call to
        # load the default intentions means the handler doesn't read from the cache,
        # because the first request included enrollable intentions.
        # We make this assertion using the returned value from the mock call
        # to fetch default intention status. In a production-like setting, this
        # second call should contain data indicating that default enrollment
        # intentions were actually realized.
        handler.load_default_enterprise_enrollment_intentions()
        self.assertEqual(
            handler.context.data['default_enterprise_enrollment_intentions'],
            mock_get_intentions.return_value,
        )


class TestDashboardHandler(TestHandlerContextMixin):
    """
    Test DashboardHandler
    """

    def setUp(self):
        super().setUp()

        self.mock_original_enterprise_course_enrollment = {
            "course_run_id": "course-v1:BabsonX+MIS01x+1T2019",
            "course_run_status": "in_progress",
            "created": "2023-09-29T14:24:45.409031+00:00",
            "start_date": "2019-03-19T10:00:00Z",
            "end_date": "2024-12-31T04:30:00Z",
            "display_name": "AI for Leaders",
            "due_dates": [],
            "pacing": "self",
            "org_name": "BabsonX",
            "is_revoked": False,
            "is_enrollment_active": True,
            "mode": "verified",
            "course_run_url": "https://learning.edx.org/course/course-v1:BabsonX+MIS01x+1T2019/home",
            "certificate_download_url": None,
            "resume_course_run_url": None,
            "course_key": "BabsonX+MIS01x",
            "course_type": "verified-audit",
            "product_source": "edx",
            "enroll_by": "2024-12-21T23:59:59Z",
            "emails_enabled": False,
            "micromasters_title": None,
        }
        self.mock_transformed_enterprise_course_enrollment = {
            "course_run_id": self.mock_original_enterprise_course_enrollment['course_run_id'],
            "course_run_status": self.mock_original_enterprise_course_enrollment['course_run_status'],
            "created": self.mock_original_enterprise_course_enrollment['created'],
            "start_date": self.mock_original_enterprise_course_enrollment['start_date'],
            "end_date": self.mock_original_enterprise_course_enrollment['end_date'],
            "title": self.mock_original_enterprise_course_enrollment['display_name'],
            "notifications": self.mock_original_enterprise_course_enrollment['due_dates'],
            "pacing": self.mock_original_enterprise_course_enrollment['pacing'],
            "org_name": self.mock_original_enterprise_course_enrollment['org_name'],
            "is_revoked": self.mock_original_enterprise_course_enrollment['is_revoked'],
            "is_enrollment_active": self.mock_original_enterprise_course_enrollment['is_enrollment_active'],
            "mode": self.mock_original_enterprise_course_enrollment['mode'],
            "link_to_course": self.mock_original_enterprise_course_enrollment['course_run_url'],
            "link_to_certificate": None,
            "resume_course_run_url": None,
            "course_key": self.mock_original_enterprise_course_enrollment['course_key'],
            "course_type": self.mock_original_enterprise_course_enrollment['course_type'],
            "product_source": self.mock_original_enterprise_course_enrollment['product_source'],
            "enroll_by": self.mock_original_enterprise_course_enrollment['enroll_by'],
            "can_unenroll": True,
            "has_emails_enabled": self.mock_original_enterprise_course_enrollment['emails_enabled'],
            "micromasters_title": self.mock_original_enterprise_course_enrollment['micromasters_title'],
        }
        self.mock_original_enterprise_course_enrollments = [self.mock_original_enterprise_course_enrollment]
        self.mock_transformed_enterprise_course_enrollments = [self.mock_transformed_enterprise_course_enrollment]

    @mock.patch('enterprise_access.apps.api_client.lms_client.LmsUserApiClient.get_enterprise_customers_for_user')
    @mock.patch('enterprise_access.apps.api_client.lms_client.LmsUserApiClient.get_enterprise_course_enrollments')
    def test_load_and_process(
        self,
        mock_get_enterprise_course_enrollments,
        mock_get_enterprise_customers_for_user,
    ):
        mock_get_enterprise_customers_for_user.return_value = self.mock_enterprise_learner_response_data
        mock_get_enterprise_course_enrollments.return_value = self.mock_original_enterprise_course_enrollments

        context = HandlerContext(self.request)
        dashboard_handler = DashboardHandler(context)

        dashboard_handler.load_and_process()

        self.assertEqual(
            dashboard_handler.context.data.get('enterprise_course_enrollments'),
            self.mock_transformed_enterprise_course_enrollments,
        )
