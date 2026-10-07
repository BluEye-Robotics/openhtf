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
"""Tests for the JSON output callback."""

import io
import json
import unittest

import openhtf
from openhtf.output.callbacks import json_factory
from openhtf.util import data


def attaching(test):
  test.attach('a.json', b'{}', 'application/json')


class JsonFactoryTest(unittest.TestCase):

  def test_inlining_attachments_leaves_the_record_serializable(self):
    """The callback must not write Attachment objects into the record's own
    cached phases, which the station server publishes after it."""
    outputs = {}

    def on_record(record):
      buffer = io.StringIO()
      json_factory.OutputToJSON(buffer, inline_attachments=True)(record)
      outputs['json'] = buffer.getvalue()
      outputs['after'] = json.dumps(data.convert_to_base_types(record))

    test = openhtf.Test(attaching)
    test.add_output_callbacks(on_record)
    test.execute(test_start=lambda: 'dut')

    written = json.loads(outputs['json'])
    self.assertIn('a.json', written['phases'][0]['attachments'])
    after = json.loads(outputs['after'])
    self.assertEqual(after['phases'][0]['attachments']['a.json']['mimetype'],
                     'application/json')


if __name__ == '__main__':
  unittest.main()
