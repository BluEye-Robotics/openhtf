# Copyright 2026 Blueye Robotics AS
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""The station's Production/Test mode: CONF.production, taken by each run as
its DUT is entered, and set through /station/mode."""

import json
import threading
import unittest
from unittest import mock

import openhtf
from openhtf.output.servers import station_server
from openhtf.util import configuration
import tornado.testing
import tornado.web

CONF = configuration.CONF


def run_test(test_start, *phases):
  """Execute a test; its record."""
  records = []
  test = openhtf.Test(*(phases or (lambda: None,)))
  test.add_output_callbacks(records.append)
  test.execute(test_start=test_start)
  return records[0]


class RunModeTest(unittest.TestCase):

  def tearDown(self):
    CONF.load(production=True)
    super().tearDown()

  def test_a_run_counts_as_production_by_default(self):
    record = run_test(lambda: 'DUT-1')
    self.assertIs(record.metadata['config']['production'], True)

  def test_a_run_takes_the_mode_that_holds_when_its_dut_is_entered(self):
    # The station waits at the DUT prompt with the config already
    # snapshotted; the operator switches to test mode before entering it.
    def enter_dut():
      CONF.load(production=False)
      return 'DUT-1'

    record = run_test(enter_dut)
    self.assertIs(record.metadata['config']['production'], False)

  def test_a_switch_during_a_run_leaves_the_run_as_it_started(self):
    def switch(test):
      del test  # Unused.
      CONF.load(production=False)

    record = run_test(lambda: 'DUT-1', openhtf.PhaseOptions()(switch))
    self.assertIs(record.metadata['config']['production'], True)

  def test_the_record_written_out_carries_the_mode(self):
    def enter_dut():
      CONF.load(production=False)
      return 'DUT-1'

    record = run_test(enter_dut)
    self.assertIs(record.as_base_types()['metadata']['config']['production'],
                  False)


class StationModeHandlerTest(tornado.testing.AsyncHTTPTestCase):

  def get_app(self):
    return tornado.web.Application([(r'/station/mode',
                                     station_server.StationModeHandler)])

  def setUp(self):
    super().setUp()
    patcher = mock.patch.object(station_server.StationPubSub, 'publish_mode')
    self.publish_mode = patcher.start()
    self.addCleanup(patcher.stop)

  def tearDown(self):
    CONF.load(production=True)
    super().tearDown()

  def mode(self):
    return json.loads(self.fetch('/station/mode').body)

  def post(self, body):
    return self.fetch('/station/mode', method='POST', body=body)

  def test_the_mode_is_read_and_set(self):
    self.assertEqual(self.mode(), {'production': True})
    response = self.post(json.dumps({'production': False}))
    self.assertEqual(response.code, 200)
    self.assertEqual(json.loads(response.body), {'production': False})
    self.assertIs(CONF.production, False)
    self.assertEqual(self.mode(), {'production': False})
    self.publish_mode.assert_called_once_with()

  def test_anything_but_a_bool_is_refused(self):
    for body in ('', 'nope', '{}', '{"production": "false"}', '{"production": 0}'):
      self.assertEqual(self.post(body).code, 400, body)
    self.assertIs(CONF.production, True)
    self.publish_mode.assert_not_called()


class ModeMessagesTest(unittest.TestCase):

  def tearDown(self):
    CONF.load(production=True)
    super().tearDown()

  def test_a_change_goes_to_every_subscriber(self):
    with mock.patch.object(station_server.pub_sub.PubSub, 'publish') as publish:
      station_server.set_production(False)
    publish.assert_called_once_with({'type': 'mode', 'production': False})

  def test_a_new_subscriber_hears_the_mode_first(self):
    CONF.load(production=False)
    subscriber = station_server.StationPubSub.__new__(station_server.StationPubSub)
    sent = []
    subscriber.send = sent.append
    with mock.patch.object(station_server, '_get_executing_tests', return_value=[]):
      subscriber.on_subscribe(None)
    self.assertEqual(sent, [{'type': 'mode', 'production': False}])

  def test_a_station_starts_in_production(self):
    CONF.load(production=False, station_server_port=0)
    server = station_server.StationServer()
    try:
      self.assertIs(CONF.production, True)
    finally:
      server.station_multicast.stop = lambda *a, **k: None  # Never started.
      server.stop()


if __name__ == '__main__':
  unittest.main()
