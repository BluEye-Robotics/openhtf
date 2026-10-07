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
"""Tests for the station server with several tests executing at once."""

import threading
import unittest

import openhtf
from openhtf.output.servers import station_server


class ParallelTestsTest(unittest.TestCase):
  """Two tests execute side by side; the server tells them apart."""

  def setUp(self):
    super().setUp()
    self.release = threading.Event()
    self.started = threading.Barrier(3)  # Two tests and the test case.
    self.records = {}

    def hold(test):
      test.measurements.held = True
      self.started.wait(timeout=10)
      self.release.wait(timeout=10)

    phase = openhtf.measures(openhtf.Measurement('held'))(hold)

    def run(name):
      test = openhtf.Test(phase, test_name=name)
      test.add_output_callbacks(self.on_record)
      test.execute(test_start=lambda: name)

    self.threads = [
        threading.Thread(target=run, args=(name,), daemon=True)
        for name in ('first', 'second')
    ]
    for thread in self.threads:
      thread.start()
    self.started.wait(timeout=10)

  def tearDown(self):
    self.release.set()
    for thread in self.threads:
      thread.join(timeout=10)
    super().tearDown()

  def on_record(self, record):
    # Output callbacks run while the test is still in TEST_INSTANCES, so the
    # record can be matched to its execution.
    self.records[record.dut_id] = (
        record, station_server._execution_uid_for_record(record))

  def test_every_executing_test_is_served(self):
    tests = station_server._get_executing_tests()
    self.assertEqual(
        sorted(state.test_record.dut_id for _, state in tests),
        ['first', 'second'])
    for test, state in tests:
      self.assertEqual(
          station_server._get_test_by_uid(state.execution_uid), (test, state))
    self.assertEqual(station_server._get_test_by_uid('nope'), (None, None))
    self.assertEqual(station_server._get_executing_test(), tests[0])

  def test_records_are_matched_to_their_execution(self):
    uids = {
        state.test_record.dut_id: state.execution_uid
        for _, state in station_server._get_executing_tests()
    }
    self.release.set()
    for thread in self.threads:
      thread.join(timeout=10)
    self.assertEqual(
        {dut: uid for dut, (_, uid) in self.records.items()}, uids)
    self.assertEqual(station_server._get_executing_tests(), [])

  def test_watchers_publish_each_test(self):
    published = {}
    done = threading.Event()

    def update(state_dict):
      published[state_dict['execution_uid']] = state_dict['test_record']['dut_id']
      if len(published) == 2:
        done.set()

    watcher = station_server.StationWatcher(update)
    watcher._watch_new_tests()
    self.assertTrue(done.wait(timeout=10))
    self.assertEqual(sorted(published.values()), ['first', 'second'])
    self.assertEqual(len(watcher._watchers), 2)
    self.release.set()
    for thread in self.threads:
      thread.join(timeout=10)
    for test_watcher in watcher._watchers.values():
      test_watcher.join(timeout=10)
      self.assertFalse(test_watcher.is_alive())


if __name__ == '__main__':
  unittest.main()
