#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import uuid

from six.moves import http_client

from keystone.common import provider_api
import keystone.conf
from keystone.tests.common import auth as common_auth
from keystone.tests import unit
from keystone.tests.unit import base_classes
from keystone.tests.unit import ksfixtures

CONF = keystone.conf.CONF
PROVIDERS = provider_api.ProviderAPIs


class _SystemUserMappingTests(object):

    def test_user_can_list_mappings(self):
        mapping = unit.new_mapping_ref()
        mapping = PROVIDERS.federation_api.create_mapping(
            mapping['id'], mapping
        )

        with self.test_client() as c:
            r = c.get('/v3/OS-FEDERATION/mappings', headers=self.headers)
            self.assertEqual(1, len(r.json['mappings']))
            self.assertEqual(mapping['id'], r.json['mappings'][0]['id'])

    def test_user_can_get_a_mapping(self):
        mapping = unit.new_mapping_ref()
        mapping = PROVIDERS.federation_api.create_mapping(
            mapping['id'], mapping
        )

        with self.test_client() as c:
            c.get(
                '/v3/OS-FEDERATION/mappings/%s' % mapping['id'],
                headers=self.headers
            )


class SystemReaderTests(base_classes.TestCaseWithBootstrap,
                        common_auth.AuthTestMixin,
                        _SystemUserMappingTests):

    def setUp(self):
        super(SystemReaderTests, self).setUp()
        self.loadapp()
        self.useFixture(ksfixtures.Policy(self.config_fixture))
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        system_reader = unit.new_user_ref(
            domain_id=CONF.identity.default_domain_id
        )
        self.user_id = PROVIDERS.identity_api.create_user(
            system_reader
        )['id']
        PROVIDERS.assignment_api.create_system_grant_for_user(
            self.user_id, self.bootstrapper.reader_role_id
        )

        auth = self.build_authentication_request(
            user_id=self.user_id, password=system_reader['password'],
            system=True
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}

    def test_user_cannot_create_mappings(self):
        create = {
            'mapping': {
                'id': uuid.uuid4().hex,
                'rules': [{
                    'local': [{'user': {'name': '{0}'}}],
                    'remote': [{'type': 'UserName'}],
                }]
            }
        }
        mapping_id = create['mapping']['id']

        with self.test_client() as c:
            c.put(
                '/v3/OS-FEDERATION/mappings/%s' % mapping_id, json=create,
                headers=self.headers,
                expected_status_code=http_client.FORBIDDEN
            )

    def test_user_cannot_update_mappings(self):
        mapping = unit.new_mapping_ref()
        mapping = PROVIDERS.federation_api.create_mapping(
            mapping['id'], mapping
        )

        update = {
            'mapping': {
                'rules': [{
                    'local': [{'user': {'name': '{0}'}}],
                    'remote': [{'type': 'UserName'}],
                }]
            }
        }

        with self.test_client() as c:
            c.patch(
                '/v3/OS-FEDERATION/mappings/%s' % mapping['id'],
                json=update, headers=self.headers,
                expected_status_code=http_client.FORBIDDEN
            )

    def test_user_cannot_delete_mappings(self):
        mapping = unit.new_mapping_ref()
        mapping = PROVIDERS.federation_api.create_mapping(
            mapping['id'], mapping
        )

        with self.test_client() as c:
            c.delete(
                '/v3/OS-FEDERATION/mappings/%s' % mapping['id'],
                headers=self.headers,
                expected_status_code=http_client.FORBIDDEN
            )
