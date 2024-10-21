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

import { Component, OnInit, Inject, forwardRef } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { plainToClass } from 'class-transformer';
import { Pipeline } from 'app/models/pipeline';
import { PipelinesService } from './shared/pipelines.service';
import { AppComponent } from 'app/app.component';

@Component({
  selector: 'app-pipelines',
  templateUrl: './pipelines.component.html',
  styleUrls: ['./pipelines.component.sass']
})
export class PipelinesComponent implements OnInit {

  pipelines: Pipeline[] = [];
  displayedPipelines: Pipeline[] = [];
  currentPage: number = 1;
  itemsPerPage: number = 10;
  totalPages: number = 0;
  totalPipelines: number = 0;
  filesToUpload: Array<File> = [];
  filterTimeout: any;
  filterText: string = '';
  state: 'loading' | 'loaded' | 'error' = 'loading';
  timeZone: string;

  private requestCounter = 0;

  constructor(
    private pipelinesService: PipelinesService,
    @Inject(forwardRef(() => AppComponent)) private appComponent: AppComponent
  ) { }

  ngOnInit() {
    this.timeZone = this.getShortTimeZone();
    this.loadPipelines(this.currentPage, this.itemsPerPage);
  }

  getShortTimeZone(): string {
    const fullTimeZone = new Intl.DateTimeFormat().resolvedOptions().timeZone;
    const date = new Date();
    return date.toLocaleTimeString('en-US', { timeZone: fullTimeZone, timeZoneName: 'short' }).split(' ').pop() || fullTimeZone;
  }

  formatToLocalTimezone(utcTime: string | null): string {
    if (!utcTime) {
      return ''; // Return empty string if the date is invalid or null
    }

    try {
      const date = new Date(utcTime + 'Z'); // 'Z' ensures it's treated as UTC
      if (isNaN(date.getTime())) {
        throw new Error('Invalid time value');
      }

      const options: Intl.DateTimeFormatOptions = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false, // To match the format you want
        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
      };

      // Use 'en-US' locale for formatting
      const formattedDate = new Intl.DateTimeFormat('en-US', options).format(date);

      // Reformat the string to 'YYYY-MM-DD HH:mm:ss'
      const [month, day, year] = formattedDate.split(', ')[0].split('/');
      const time = formattedDate.split(', ')[1];

      return `${year}-${month}-${day} ${time}`;
    } catch (error) {
      console.error('Error formatting date:', error);
      return 'Invalid Date'; // Return a fallback string for invalid dates
    }
  }

  loadPipelines(page: number, itemsPerPage: number) {
    this.state = 'loading';
    const currentRequestId = ++this.requestCounter;
    this.pipelinesService.getPipelines(page, itemsPerPage, this.filterText).then(
      (response: any) => {
        if (currentRequestId === this.requestCounter) {
          if (response && Array.isArray(response.pipelines)) {
            this.pipelines = response.pipelines.map(
              pipelineData => new Pipeline(pipelineData));
            this.displayedPipelines = this.pipelines;
            this.totalPipelines = response.total || 0;
            this.totalPages = Math.ceil(
              this.totalPipelines / this.itemsPerPage);
            this.currentPage = response.page;
            this.itemsPerPage = response.itemsPerPage;
            this.state = 'loaded';
          } else {
            console.error('Unexpected response structure:', response);
            this.state = 'error';
          }
        }
      },
      error => {
        if (currentRequestId === this.requestCounter) {
          console.error('Error loading pipelines:', error);
          this.state = 'error';
        }
      }
    );
  }

  /**
   * Generic method to reset the pipeline data.
   */
  resetPipelineData() {
    this.currentPage = 1;
    this.loadPipelines(this.currentPage, this.itemsPerPage);
  }

  onFilterChange() {
    if (this.filterTimeout) {
      clearTimeout(this.filterTimeout);
    }
    this.filterTimeout = setTimeout(() => {
      this.resetPipelineData();
    }, 300);
  }

  onPageChange(event: PageEvent) {
    this.loadPipelines(event.pageIndex + 1, event.pageSize);
  }

  deletePipeline(pipeline) {
    if (confirm(`Are you sure you want to delete ${pipeline.name}?`)) {
      const index = this.pipelines.indexOf(pipeline);
      if (index !== -1) {
        this.pipelinesService.deletePipeline(pipeline.id).then(
          () => {
            this.totalPipelines--;
            if (this.displayedPipelines.length === 1 && this.currentPage > 1) {
              this.currentPage--;
            }
            this.loadPipelines(this.currentPage, this.itemsPerPage);
          },
          (err) => {
            console.log('Error deleting pipeline', err);
            this.appComponent.addAlert('Failed to delete pipeline.');
          }
        );
      }
    }
  }

  updateDisplayedPipelines() {
    const start = (this.currentPage - 1) * this.itemsPerPage;
    const end = start + this.itemsPerPage;
    this.displayedPipelines = this.pipelines.slice(start, end);
  }

  importPipeline(data) {
    this.pipelinesService.importPipeline(data.target.files[0]).then(
      (pipeline) => {
        const importedPipeline = plainToClass(Pipeline, pipeline as Pipeline);
        this.pipelines.push(importedPipeline);
        this.totalPipelines++;
        this.updateDisplayedPipelines();
        this.totalPages = Math.ceil(this.totalPipelines / this.itemsPerPage);
        if (this.pipelines.length > this.itemsPerPage) {
          this.currentPage = this.totalPages;
          this.loadPipelines(this.currentPage, this.itemsPerPage);
        }
      },
      (error) => {
        console.error('Error importing pipeline:', error);
        this.appComponent.addAlert('Failed to import pipeline.');
      }
    );
  }
}
