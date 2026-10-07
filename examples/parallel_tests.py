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
"""Several tests executing at once in one process, one panel each in the GUI.

A station with several fixtures (slots) runs one test per slot from its own
thread; every test has its own DUT ID, record and operator prompts. Each
slot here loops: a start prompt asking for the DUT ID, a prompt to press OK,
a short measured phase, and the next run.

    python examples/parallel_tests.py          # 4 slots on port 4444
    PARALLEL_SLOTS=2 python examples/parallel_tests.py
"""

import os
import threading
import time

import openhtf as htf
from openhtf.output.servers import station_server
from openhtf.output.web_gui import web_launcher
from openhtf.plugs import user_input
from openhtf.util import conf


@htf.plug(prompts=user_input.UserInput)
def confirm_fixture(test, prompts, slot):
  prompts.prompt('Slot %d: press OK when the unit is in the fixture.' % slot)


@htf.measures(htf.Measurement('slot'), htf.Measurement('elapsed_s').in_range(0, 60))
def measure(test, slot, seconds):
  test.measurements.slot = slot
  for n in range(seconds):
    test.logger.info('Slot %d: %d of %d s', slot, n + 1, seconds)
    time.sleep(1)
  test.measurements.elapsed_s = seconds


def run_slot(server, slot, seconds):
  while True:
    test = htf.Test(
        confirm_fixture.with_args(slot=slot),
        measure.with_args(slot=slot, seconds=seconds),
        test_name='slot-%d' % slot,
    )
    test.add_output_callbacks(server.publish_final_state)
    test.execute(test_start=user_input.prompt_for_test_start(
        'Slot %d: enter the DUT ID to start.' % slot))


def main():
  slots = int(os.environ.get('PARALLEL_SLOTS', '4'))
  seconds = int(os.environ.get('PARALLEL_SECONDS', '20'))
  conf.load(station_server_port=os.environ.get('STATION_SERVER_PORT', '4444'),
            station_id='parallel-example')
  with station_server.StationServer() as server:
    web_launcher.launch('http://localhost:%s' % server.port)
    threads = [
        threading.Thread(target=run_slot, args=(server, slot, seconds),
                         name='slot-%d' % slot, daemon=True)
        for slot in range(1, slots + 1)
    ]
    for thread in threads:
      thread.start()
    for thread in threads:
      thread.join()


if __name__ == '__main__':
  main()
