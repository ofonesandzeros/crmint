// Copyright 2024 Google Inc
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import { TestBed } from '@angular/core/testing';
import { TimezoneService } from './timezone.service';

describe('TimezoneService', () => {
  let service: TimezoneService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(TimezoneService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should return a short timezone', () => {
    const shortTimeZone = service.getShortTimeZone();
    expect(shortTimeZone).toBeDefined();
    expect(typeof shortTimeZone).toBe('string');
  });

  it('should format UTC time to local timezone', () => {
    const utcTime = '2023-10-05T14:48:00.000Z';
    const formattedTime = service.formatToLocalTimezone(utcTime);
    expect(formattedTime).toBeDefined();
    expect(typeof formattedTime).toBe('string');
  });

  it('should handle null input for formatToLocalTimezone', () => {
    const formattedTime = service.formatToLocalTimezone(null);
    expect(formattedTime).toBe('');
  });

  it('should handle invalid date input for formatToLocalTimezone', () => {
    const formattedTime = service.formatToLocalTimezone('invalid-date');
    expect(formattedTime).toBe('Invalid Date');
  });
});