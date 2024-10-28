// Copyright 2018 Google Inc
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

import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { environment } from 'environments/environment';
import { PipelinesService } from 'app/pipelines/shared/pipelines.service';

@Component({
  selector: 'app-nav-bar',
  templateUrl: './nav-bar.component.html',
  styleUrls: ['./nav-bar.component.sass']
})
export class NavBarComponent implements OnInit {
  enabled_stages: boolean = environment.enabled_stages;

  constructor(private router: Router, private pipelinesService: PipelinesService) { }

  ngOnInit() {
  }

  navigateToPipelines() {
    // Reset pagination state
    const page = 1;
    const itemsPerPage = 10;
    const filter = '';

    // Make API request to fetch the first page of pipelines
    this.pipelinesService.getPipelines(page, itemsPerPage, filter).then(pipelines => {
      // Handle the pipelines data as needed
      console.log('Pipelines:', pipelines);
    });

    // Navigate to the pipelines view
    this.router.navigate(['/pipelines']);
  }
}
