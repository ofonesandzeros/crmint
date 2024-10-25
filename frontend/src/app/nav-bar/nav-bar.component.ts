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
import { Router, ActivatedRoute, NavigationEnd } from '@angular/router';
import { environment } from 'environments/environment';

@Component({
  selector: 'app-nav-bar',
  templateUrl: './nav-bar.component.html',
  styleUrls: ['./nav-bar.component.sass']
})
export class NavBarComponent implements OnInit {
  enabled_stages: boolean = environment.enabled_stages;

  constructor(private router: Router) { }

  ngOnInit() {
    this.router.events.subscribe(event => {
      if (event instanceof NavigationEnd) {
        this.router.routeReuseStrategy.shouldReuseRoute = () => true;
        this.router.onSameUrlNavigation = 'ignore';
      }
    });
  }

  refreshPipelines() {
    this.router.routeReuseStrategy.shouldReuseRoute = (route) => {
      return route.routeConfig?.path !== 'pipelines';
    };
    this.router.onSameUrlNavigation = 'reload';
    this.router.navigate(['/pipelines']).then(() => {
      this.router.routeReuseStrategy.shouldReuseRoute = () => true;
      this.router.onSameUrlNavigation = 'ignore';
    });
  }
}
