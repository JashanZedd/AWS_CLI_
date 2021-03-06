# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from awscli.testutils import unittest
from awscli.customizations.ecs.deploy import (CodeDeployValidator,
                                              TIMEOUT_BUFFER_MIN)
from awscli.customizations.ecs.exceptions import (InvalidPlatformError,
                                                  InvalidProperyError)


class TestCodeDeployValidator(unittest.TestCase):
    TEST_RESOURCES = {
        'service': 'test-service',
        'service_arn': 'arn:aws:ecs:::service/test-service',
        'cluster': 'test-cluster',
        'cluster_arn': 'arn:aws:ecs:::cluster/test-cluster',
        'app_name': 'test-application',
        'deployment_group_name': 'test-deployment-group'
    }

    TEST_APP_DETAILS = {
        'application': {
            'applicationId': '876uyh6-45tdfg',
            'applicationName': 'test-application',
            'computePlatform': 'ECS'
        }
    }

    TEST_DEPLOYMENT_GROUP_DETAILS = {
        'deploymentGroupInfo': {
            'applicationName': 'test-application',
            'deploymentGroupName': 'test-deployment-group',
            'computePlatform': 'ECS',
            'blueGreenDeploymentConfiguration': {
                'deploymentReadyOption': {
                    'waitTimeInMinutes': 5
                },
                'terminateBlueInstancesOnDeploymentSuccess': {
                    'terminationWaitTimeInMinutes': 10
                }
            },
            'ecsServices': [{
                'serviceName': 'test-service',
                'clusterName': 'test-cluster'
            }],
            'deploymentConfigName': 'CodeDeployDefault.ECSLinear10PercentEvery1Minutes'
        }
    }

    def setUp(self):
        self.validator = CodeDeployValidator(None, self.TEST_RESOURCES)
        self.validator.app_details = self.TEST_APP_DETAILS
        self.validator.deployment_group_details = \
            self.TEST_DEPLOYMENT_GROUP_DETAILS

    def test_get_deployment_wait_time(self):
        actual_wait = self.validator.get_deployment_wait_time()
        self.assertEqual(15, actual_wait)

    def test_get_traffic_rerouting_missing_traffic_routing_config(self):
        self.validator.deployment_config_details = {
            'deploymentConfigInfo': {}
        }

        actual_wait = self.validator.get_traffic_rerouting_time()
        self.assertEqual(0, actual_wait)

    def test_get_traffic_rerouting_time_based_linear(self):
        self.validator.deployment_config_details = {
            'deploymentConfigInfo': {
                'trafficRoutingConfig': {
                    'type': 'TimeBasedLinear',
                    'timeBasedLinear': {
                        'linearPercentage': 10,
                        'linearInterval': 5
                    }
                }
            }
        }

        actual_wait = self.validator.get_traffic_rerouting_time()
        self.assertEqual(10 * 5, actual_wait)

    def test_get_traffic_rerouting_time_based_canary(self):
        self.validator.deployment_config_details = {
            'deploymentConfigInfo': {
                'trafficRoutingConfig': {
                    'type': 'TimeBasedCanary',
                    'timeBasedCanary': {
                        'canaryPercentage': 10,
                        'canaryInterval': 5
                    }
                }
            }
        }

        actual_wait = self.validator.get_traffic_rerouting_time()
        self.assertEqual(5, actual_wait)

    def test_get_traffic_rerouting_time_all_at_once(self):
        self.validator.deployment_config_details = {
            'deploymentConfigInfo': {
                'trafficRoutingConfig': {
                    'type': 'AllAtOnce'
                }
            }
        }

        actual_wait = self.validator.get_traffic_rerouting_time()
        self.assertEqual(0, actual_wait)

    def test_get_traffic_rerouting_time_unknown_traffic_routing_config(self):
        self.validator.deployment_config_details = {
            'deploymentConfigInfo': {
                'trafficRoutingConfig': {
                    'type': 'NewTypeNotKnownYet'
                }
            }
        }

        actual_wait = self.validator.get_traffic_rerouting_time()
        self.assertEqual(0, actual_wait)

    def test_get_deployment_duration(self):
        expected_wait = 5 + 10 + TIMEOUT_BUFFER_MIN
        actual_wait = self.validator.get_deployment_duration()
        self.assertEqual(expected_wait, actual_wait)

    def test_get_deployment_duration_no_dgp(self):
        empty_validator = CodeDeployValidator(None, self.TEST_RESOURCES)
        actual_wait = empty_validator.get_deployment_duration()
        self.assertEqual(TIMEOUT_BUFFER_MIN, actual_wait)

    def test_validations(self):
        self.validator.validate_application()
        self.validator.validate_deployment_group()
        self.validator.validate_all()

    def test_validate_application_error_compute_platform(self):
        invalid_app = {
            'application': {
                'applicationName': 'test-application',
                'computePlatform': 'Server'
            }
        }

        bad_validator = CodeDeployValidator(None, self.TEST_RESOURCES)
        bad_validator.app_details = invalid_app

        with self.assertRaises(InvalidPlatformError):
            bad_validator.validate_application()

    def test_validate_deployment_group_error_compute_platform(self):
        invalid_dgp = {
            'deploymentGroupInfo': {
                'computePlatform': 'Lambda'
            }
        }
        bad_validator = CodeDeployValidator(None, self.TEST_RESOURCES)
        bad_validator.deployment_group_details = invalid_dgp

        with self.assertRaises(InvalidPlatformError):
            bad_validator.validate_deployment_group()

    def test_validate_deployment_group_error_service(self):
        invalid_dgp = {
            'deploymentGroupInfo': {
                'computePlatform': 'ECS',
                'ecsServices': [{
                    'serviceName': 'the-wrong-test-service',
                    'clusterName': 'test-cluster'
                }]
            }
        }
        bad_validator = CodeDeployValidator(None, self.TEST_RESOURCES)
        bad_validator.deployment_group_details = invalid_dgp

        with self.assertRaises(InvalidProperyError):
            bad_validator.validate_deployment_group()

    def test_validate_deployment_group_error_cluster(self):
        invalid_dgp = {
            'deploymentGroupInfo': {
                'computePlatform': 'ECS',
                'ecsServices': [{
                    'serviceName': 'test-service',
                    'clusterName': 'the-wrong-test-cluster'
                }]
            }
        }
        bad_validator = CodeDeployValidator(None, self.TEST_RESOURCES)
        bad_validator.deployment_group_details = invalid_dgp

        with self.assertRaises(InvalidProperyError):
            bad_validator.validate_deployment_group()
