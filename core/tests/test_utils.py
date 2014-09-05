# Copyright 2014 The Oppia Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Common utilities for test classes."""

import contextlib
import os
import re
import unittest
import webtest

from core.domain import config_domain
from core.domain import exp_domain
from core.domain import exp_services
from core.platform import models
current_user_services = models.Registry.import_current_user_services()
import feconf
import main

import json


CSRF_REGEX = (
    r'csrf_token: JSON\.parse\(\'\\\"([A-Za-z0-9/=_-]+)\\\"\'\)')
# Prefix to append to all lines printed by tests to the console.
LOG_LINE_PREFIX = 'LOG_INFO_TEST: '


def empty_environ():
    os.environ['AUTH_DOMAIN'] = 'example.com'
    os.environ['SERVER_NAME'] = 'localhost'
    os.environ['HTTP_HOST'] = 'localhost'
    os.environ['SERVER_PORT'] = '8080'
    os.environ['USER_EMAIL'] = ''
    os.environ['USER_ID'] = ''
    os.environ['USER_IS_ADMIN'] = '0'
    os.environ['DEFAULT_VERSION_HOSTNAME'] = '%s:%s' % (
        os.environ['HTTP_HOST'], os.environ['SERVER_PORT'])


class TestBase(unittest.TestCase):
    """Base class for all tests."""

    maxDiff = 2500

    DEFAULT_USERNAME = 'defaultusername'

    def setUp(self):
        raise NotImplementedError

    def tearDown(self):
        raise NotImplementedError

    def log_line(self, line):
        """Print the line with a prefix that can be identified by the
        script that calls the test.
        """
        print '%s%s' % (LOG_LINE_PREFIX, line)

    def _delete_all_models(self):
        raise NotImplementedError

    def _stash_current_user_env(self):
        """Stashes the current user-specific env variables for later retrieval.

        Developers: please don't use this method outside this class -- it makes
        the individual tests harder to follow.
        """
        self.stashed_user_env = {
            'USER_EMAIL': os.environ['USER_EMAIL'],
            'USER_ID': os.environ['USER_ID'],
            'USER_IS_ADMIN': os.environ['USER_IS_ADMIN']
        }

    def _restore_stashed_user_env(self):
        """Restores a stashed set of user-specific env variables.

        Developers: please don't use this method outside this class -- it makes
        the individual tests harder to follow.
        """
        if not self.stashed_user_env:
            raise Exception('No stashed user env to restore.')

        for key in self.stashed_user_env:
            os.environ[key] = self.stashed_user_env[key]

        self.stashed_user_env = None

    def login(self, email, is_super_admin=False):
        os.environ['USER_EMAIL'] = email
        os.environ['USER_ID'] = self.get_user_id_from_email(email)
        os.environ['USER_IS_ADMIN'] = '1' if is_super_admin else '0'

    def logout(self):
        os.environ['USER_EMAIL'] = ''
        os.environ['USER_ID'] = ''
        os.environ['USER_IS_ADMIN'] = '0'

    def shortDescription(self):
        """Additional information logged during unit test invocation."""
        # Suppress default logging of docstrings.
        return None

    def get_expected_login_url(self, slug):
        """Returns the expected login URL."""
        return current_user_services.create_login_url(slug)

    def get_expected_logout_url(self, slug):
        """Returns the expected logout URL."""
        return current_user_services.create_logout_url(slug)

    def _parse_json_response(self, json_response, expect_errors=False):
        """Convert a JSON server response to an object (such as a dict)."""
        if not expect_errors:
            self.assertEqual(json_response.status_int, 200)

        self.assertEqual(
            json_response.content_type, 'application/javascript')
        self.assertTrue(json_response.body.startswith(feconf.XSSI_PREFIX))

        return json.loads(json_response.body[len(feconf.XSSI_PREFIX):])

    def get_json(self, url):
        """Get a JSON response, transformed to a Python object."""
        json_response = self.testapp.get(url)
        self.assertEqual(json_response.status_int, 200)
        return self._parse_json_response(json_response, expect_errors=False)

    def post_json(self, url, payload, csrf_token=None, expect_errors=False,
                  expected_status_int=200, upload_files=None):
        """Post an object to the server by JSON; return the received object."""
        data = {'payload': json.dumps(payload)}
        if csrf_token:
            data['csrf_token'] = csrf_token

        json_response = self.testapp.post(
            str(url), data, expect_errors=expect_errors,
            upload_files=upload_files)

        self.assertEqual(json_response.status_int, expected_status_int)
        return self._parse_json_response(
            json_response, expect_errors=expect_errors)

    def put_json(self, url, payload, csrf_token=None, expect_errors=False,
                 expected_status_int=200):
        """Put an object to the server by JSON; return the received object."""
        data = {'payload': json.dumps(payload)}
        if csrf_token:
            data['csrf_token'] = csrf_token

        json_response = self.testapp.put(
            str(url), data, expect_errors=expect_errors)

        self.assertEqual(json_response.status_int, expected_status_int)
        return self._parse_json_response(
            json_response, expect_errors=expect_errors)

    def get_csrf_token_from_response(self, response):
        """Retrieve the CSRF token from a GET response."""
        return re.search(CSRF_REGEX, response.body).group(1)

    def register_editor(self, email, username=None):
        """Register a user with the given username as an editor."""
        if username is None:
            username = self.DEFAULT_USERNAME

        self.login(email)

        response = self.testapp.get(feconf.EDITOR_PREREQUISITES_URL)
        csrf_token = self.get_csrf_token_from_response(response)

        response = self.testapp.post(feconf.EDITOR_PREREQUISITES_DATA_URL, {
            'csrf_token': csrf_token,
            'payload': json.dumps({
                'username': username,
                'agreed_to_terms': True
            })
        })
        self.assertEqual(response.status_int, 200)

        self.logout()

    def set_admins(self, admin_emails):
        """Set the ADMIN_EMAILS property."""
        self._stash_current_user_env()

        self.login('superadmin@example.com', is_super_admin=True)
        response = self.testapp.get('/admin')
        csrf_token = self.get_csrf_token_from_response(response)
        self.post_json('/adminhandler', {
            'action': 'save_config_properties',
            'new_config_property_values': {
                config_domain.ADMIN_EMAILS.name: admin_emails,
            }
        }, csrf_token)
        self.logout()

        self._restore_stashed_user_env()

    def set_moderators(self, moderator_emails):
        """Set the MODERATOR_EMAILS property."""
        self._stash_current_user_env()

        self.login('superadmin@example.com', is_super_admin=True)
        response = self.testapp.get('/admin')
        csrf_token = self.get_csrf_token_from_response(response)
        self.post_json('/adminhandler', {
            'action': 'save_config_properties',
            'new_config_property_values': {
                config_domain.MODERATOR_EMAILS.name: moderator_emails,
            }
        }, csrf_token)
        self.logout()

        self._restore_stashed_user_env()

    def get_current_logged_in_user_id(self):
        return os.environ['USER_ID']

    def get_user_id_from_email(self, email):
        return current_user_services.get_user_id_from_email(email)

    def save_new_default_exploration(self,
            exploration_id, owner_id, title='A title'):
        """Saves a new default exploration written by owner_id.

        Returns the exploration domain object.
        """
        exploration = exp_domain.Exploration.create_default_exploration(
            exploration_id, title, 'A category')
        exp_services.save_new_exploration(owner_id, exploration)
        return exploration

    def save_new_valid_exploration(
            self, exploration_id, owner_id, title='A title'):
        """Saves a new strictly-validated exploration.

        Returns the exploration domain object.
        """
        exploration = exp_domain.Exploration.create_default_exploration(
            exploration_id, title, 'A category')
        exploration.states[exploration.init_state_name].widget.handlers[
            0].rule_specs[0].dest = feconf.END_DEST
        exploration.objective = 'An objective'
        exp_services.save_new_exploration(owner_id, exploration)
        return exploration

    @contextlib.contextmanager
    def swap(self, obj, attr, newvalue):
        """Swap an object's attribute value within the context of a
        'with' statement. The object can be anything that supports
        getattr and setattr, such as class instances, modules, ...

        Example usage:

        import math
        with self.swap(math, "sqrt", lambda x: 42):
            print math.sqrt(16.0) # prints 42
        print math.sqrt(16.0) # prints 4 as expected.
        """
        original = getattr(obj, attr)
        setattr(obj, attr, newvalue)
        try:
            yield
        finally:
            setattr(obj, attr, original)


class AppEngineTestBase(TestBase):
    """Base class for tests requiring App Engine services."""

    def _delete_all_models(self):
        from google.appengine.ext import ndb
        ndb.delete_multi(ndb.Query().iter(keys_only=True))

    def setUp(self):
        empty_environ()

        from google.appengine.datastore import datastore_stub_util
        from google.appengine.ext import testbed

        self.testbed = testbed.Testbed()
        self.testbed.activate()

        # Configure datastore policy to emulate instantaneously and globally
        # consistent HRD.
        policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(
            probability=1)

        # Declare any relevant App Engine service stubs here.
        self.testbed.init_user_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_datastore_v3_stub(consistency_policy=policy)
        self.testbed.init_urlfetch_stub()
        self.testbed.init_files_stub()
        self.testbed.init_blobstore_stub()

        # The root path tells the testbed where to find the queue.yaml file.
        self.testbed.init_taskqueue_stub(root_path=os.getcwd())
        self.taskqueue_stub = self.testbed.get_stub(
            testbed.TASKQUEUE_SERVICE_NAME)

        self.testbed.init_mail_stub()
        self.mail_stub = self.testbed.get_stub(testbed.MAIL_SERVICE_NAME)

        # Set up the app to be tested.
        self.testapp = webtest.TestApp(main.app)

    def tearDown(self):
        self.logout()
        self._delete_all_models()
        self.testbed.deactivate()

    def _get_all_queue_names(self):
        return [q['name'] for q in self.taskqueue_stub.GetQueues()]

    def count_jobs_in_taskqueue(self, queue_name=None):
        """Counts the jobs in the given queue. If queue_name is None,
        defaults to counting the jobs in all queues available.
        """
        if queue_name:
            return len(self.taskqueue_stub.get_filtered_tasks(
                queue_names=[queue_name]))
        else:
            return len(self.taskqueue_stub.get_filtered_tasks())

    def process_and_flush_pending_tasks(self, queue_name=None):
        """Runs and flushes pending tasks. If queue_name is None, does so for
        all queues; otherwise, this only runs and flushes tasks for the
        specified queue.

        For more information on self.taskqueue_stub see

            https://code.google.com/p/googleappengine/source/browse/trunk/python/google/appengine/api/taskqueue/taskqueue_stub.py
        """
        queue_names = [queue_name] if queue_name else self._get_all_queue_names()

        tasks = self.taskqueue_stub.get_filtered_tasks(queue_names=queue_names)
        for q in queue_names:
            self.taskqueue_stub.FlushQueue(q)

        while tasks:
            for task in tasks:
                if task.url == '/_ah/queue/deferred':
                    from google.appengine.ext import deferred
                    deferred.run(task.payload)
                else:
                    # All other tasks are expected to be mapreduce ones.
                    headers = {
                        key: str(val) for key, val in task.headers.iteritems()
                    }
                    headers['Content-Length'] = str(len(task.payload or ''))
                    response = self.testapp.post(
                        url=str(task.url), params=(task.payload or ''),
                        headers=headers)
                    if response.status_code != 200:
                        raise RuntimeError(
                            'MapReduce task to URL %s failed' % task.url)

            tasks = self.taskqueue_stub.get_filtered_tasks(
                queue_names=queue_names)
            for q in queue_names:
                self.taskqueue_stub.FlushQueue(q)


if feconf.PLATFORM == 'gae':
    GenericTestBase = AppEngineTestBase
else:
    raise Exception('Invalid platform: expected one of [\'gae\']')
