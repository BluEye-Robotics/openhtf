/**
 * Copyright 2022 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { NO_ERRORS_SCHEMA } from '@angular/core';

import { AppComponent } from './app.component';
import { ConfigService } from './core/config.service';
import { Station, StationStatus } from './shared/models/station.model';
import { StationService } from './stations/station/station.service';

class MockConfigService {
  initialize = jasmine.createSpy('initialize');
}

class MockStationService {
  production: boolean|null = null;
  isProduction = jasmine.createSpy('isProduction').and.callFake(() => this.production);
  setProduction = jasmine.createSpy('setProduction');
}

const mockStation = new Station({
  cell: null,
  host: 'localhost',
  hostPort: 'localhost:4444',
  label: 'Battery-Station',
  port: '4444',
  stationId: 'Battery-Station',
  status: StationStatus.online,
  testDescription: null,
  testName: null,
});

describe('App', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [RouterTestingModule],
      declarations: [AppComponent],
      providers: [
        { provide: ConfigService, useClass: MockConfigService },
        { provide: StationService, useClass: MockStationService },
      ],
      schemas: [NO_ERRORS_SCHEMA]
    });
  });

  it('should compile', () => {
    let fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();
    expect(fixture.componentInstance).toBeTruthy();
  });

  describe('station mode', () => {
    const render = (production: boolean|null) => {
      const fixture = TestBed.createComponent(AppComponent);
      const stations = TestBed.inject(StationService) as unknown as MockStationService;
      stations.production = production;
      fixture.componentInstance.selectedStation = mockStation;
      fixture.detectChanges();
      return {fixture, stations, element: fixture.nativeElement as HTMLElement};
    };

    it('should show no switch for a station without the mode', () => {
      const {element} = render(null);
      expect(element.querySelector('.htf-mode-switch')).toBeNull();
      expect(element.classList).not.toContain('htf-test-mode');
    });

    it('should show production plainly', () => {
      const {element} = render(true);
      expect(element.querySelector('.htf-mode-switch-option.is-active').textContent)
          .toContain('Production');
      expect(element.classList).not.toContain('htf-test-mode');
      expect(element.querySelector('.htf-test-mode-strip')).toBeNull();
    });

    it('should show test mode across the page', () => {
      const {element} = render(false);
      expect(element.classList).toContain('htf-test-mode');
      expect(element.querySelector('.htf-test-mode-strip').textContent)
          .toContain('TEST MODE');
      expect(element.querySelector('.htf-mode-switch-option.is-active').textContent)
          .toContain('Test');
    });

    it('should switch the station when the other option is clicked', () => {
      const {element, stations} = render(false);
      const production = element.querySelectorAll('.htf-mode-switch-option')[0];
      (production as HTMLButtonElement).click();
      expect(stations.setProduction).toHaveBeenCalledWith(mockStation, true);
      stations.setProduction.calls.reset();
      (element.querySelectorAll('.htf-mode-switch-option')[1] as HTMLButtonElement).click();
      expect(stations.setProduction).not.toHaveBeenCalled();  // Already in test mode.
    });
  });
});

