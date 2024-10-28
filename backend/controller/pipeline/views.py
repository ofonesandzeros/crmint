# Copyright 2024 Google Inc
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

"""Pipeline section."""

import datetime
import json
import os
import textwrap
import time
import uuid

import flask
from flask_restful import abort
from flask_restful import Api
from flask_restful import fields
from flask_restful import marshal_with
from flask_restful import reqparse
from flask_restful import Resource
from google.cloud import logging
import jinja2
from sqlalchemy import orm
import werkzeug

from common import crmint_logging
from common import insight
from controller import models
from controller.cron_utils import is_valid_cron


_PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')
_LOGS_PAGE_SIZE = 20

blueprint = flask.Blueprint('pipeline', __name__)
api = Api(blueprint)

parser = reqparse.RequestParser()
parser.add_argument('name')
parser.add_argument('emails_for_notifications')
parser.add_argument('run_on_schedule')
parser.add_argument('schedules', type=list, location='json')
parser.add_argument('params', type=list, location='json')

schedule_fields = {
    'id': fields.Integer,
    'pipeline_id': fields.Integer,
    'cron': fields.String,
}
param_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'type': fields.String,
    'value': fields.Raw(attribute='api_value'),
    'label': fields.String
}
pipeline_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'emails_for_notifications': fields.String,
    'status': fields.String,
    'updated_at': fields.String,
    'run_on_schedule': fields.Boolean,
    'schedules': fields.List(fields.Nested(schedule_fields)),
    'params': fields.List(fields.Nested(param_fields)),
    'message': fields.String,
    'has_jobs': fields.Boolean,
}
pipeline_list_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'status': fields.String,
    'updated_at': fields.String,
    'run_on_schedule': fields.Boolean,
    'schedules': fields.List(fields.Nested(schedule_fields)),
    'has_jobs': fields.Boolean
}
paginated_pipelines_fields = {
    'pipelines': fields.List(fields.Nested(pipeline_list_fields)),
    'total': fields.Integer,
    'page': fields.Integer,
    'itemsPerPage': fields.Integer
}


def abort_if_pipeline_doesnt_exist(pipeline, pipeline_id):
  if pipeline is None:
    abort(404, message="Pipeline {} doesn't exist".format(pipeline_id))


class PipelineSingle(Resource):
  """Shows a single pipeline item and lets you delete a pipeline item."""

  @marshal_with(pipeline_fields)
  def get(self, pipeline_id):
    pipeline = models.Pipeline.find(pipeline_id)
    abort_if_pipeline_doesnt_exist(pipeline, pipeline_id)
    return pipeline

  @marshal_with(pipeline_fields)
  def delete(self, pipeline_id):
    pipeline = models.Pipeline.find(pipeline_id)

    abort_if_pipeline_doesnt_exist(pipeline, pipeline_id)
    if pipeline.is_blocked():
      return {
          'message': 'Removing of active pipeline is unavailable'
      }, 422

    pipeline.destroy()
    return {}, 204

  @marshal_with(pipeline_fields)
  def put(self, pipeline_id):
    pipeline = models.Pipeline.find(pipeline_id)
    abort_if_pipeline_doesnt_exist(pipeline, pipeline_id)

    if pipeline.is_blocked():
      return {
          'message': 'Editing of active pipeline is unavailable'
      }, 422

    args = parser.parse_args()

    # Validate cron expressions in the schedules
    for schedule in args.get('schedules', []):
      cron = schedule.get('cron', '')
      if not is_valid_cron(cron):
        return {'message': f'Invalid cron expression: {cron}'}, 422

    pipeline.assign_attributes(args)
    pipeline.save()
    pipeline.save_relations(args)
    return pipeline, 200


class PipelineList(Resource):
  """Shows a list of all pipelines, and lets you POST to add new pipelines."""

  @marshal_with(paginated_pipelines_fields)
  def get(self):
    try:
      crmint_logging.log_global_message('[PipelineList.get()] Entered', log_level='DEBUG')
      parser = reqparse.RequestParser()
      parser.add_argument('page', type=int, default=1, location='args')
      parser.add_argument('itemsPerPage', type=int, default=10, location='args')
      parser.add_argument('filter', type=str, default='', location='args')
      args = parser.parse_args()
      page = args['page']
      items_per_page = args['itemsPerPage']

      tracker = insight.GAProvider()
      tracker.track_event(category='pipelines', action='list')

      query = models.Pipeline.query.options(
          orm.noload(models.Pipeline.jobs),
          orm.noload(models.Pipeline.params)
      ).order_by(models.Pipeline.updated_at.desc())
      if args['filter']:
        query = query.filter(models.Pipeline.name.ilike(f"%{args['filter']}%"))
      total_pipelines = query.count()
      crmint_logging.log_global_message(f'[PipelineList.get()] Total pipelines {total_pipelines}', log_level='DEBUG')
      pipelines = query.offset((page - 1) * items_per_page).limit(items_per_page).all()
      crmint_logging.log_global_message('[PipelineList.get()] Pipelines queried', log_level='DEBUG')
      for pipeline in pipelines:
        pipeline.updated_at = (
          pipeline.updated_at.isoformat() + 'Z'
          if pipeline.updated_at else None
        )
      crmint_logging.log_global_message('[PipelineList.get()] Returning', log_level='DEBUG')

      return {
        'pipelines': pipelines,
        'total': total_pipelines,
        'page': page,
        'itemsPerPage': items_per_page
      }
    except Exception as e:
      print(f"Error in PipelineList.get: {str(e)}")
      return {'error': 'An unexpected error occurred'}, 500

  @marshal_with(pipeline_fields)
  def post(self):
    args = parser.parse_args()
    pipeline = models.Pipeline(name=args['name'])
    pipeline.assign_attributes(args)
    pipeline.save()
    pipeline.save_relations(args)
    tracker = insight.GAProvider()
    tracker.track_event(category='pipelines', action='create')
    return pipeline, 201


class PipelineStart(Resource):
  """Class for run pipeline."""

  @marshal_with(pipeline_fields)
  def post(self, pipeline_id):
    pipeline = models.Pipeline.find(pipeline_id)
    pipeline.start(manual=True)
    tracker = insight.GAProvider()
    tracker.track_event(category='pipelines', action='manual_run')
    return pipeline


class PipelineStop(Resource):
  """Class for stopping of pipeline."""

  @marshal_with(pipeline_fields)
  def post(self, pipeline_id):
    pipeline = models.Pipeline.find(pipeline_id)
    pipeline.stop()
    tracker = insight.GAProvider()
    tracker.track_event(category='pipelines', action='manual_stop')
    return pipeline


class PipelineExport(Resource):
  """Class for exporting of pipeline in yaml format."""

  def get(self, pipeline_id):
    tracker = insight.GAProvider()
    tracker.track_event(category='pipelines', action='export')
    pipeline = models.Pipeline.find(pipeline_id)
    jobs = self._get_jobs(pipeline)

    pipeline_params = []
    for param in pipeline.params:
      pipeline_params.append({
          'name': param.name,
          'value': param.value,
          'type': param.type,
      })

    pipeline_schedules = []
    for schedule in pipeline.schedules:
      pipeline_schedules.append({
          'cron': schedule.cron,
      })

    data = {
        'name': pipeline.name,
        'run_on_schedule': pipeline.run_on_schedule,
        'jobs': jobs,
        'params': pipeline_params,
        'schedules': pipeline_schedules
    }

    ts = time.time()
    pipeline_date = datetime.datetime.fromtimestamp(ts)
    pipeline_date_formatted = pipeline_date.strftime('%Y%m%d%H%M%S')
    filename = pipeline.name.lower() + '-' + pipeline_date_formatted + '.json'
    return data, 200, {
        'Access-Control-Expose-Headers': 'Filename',
        'Content-Disposition': f'attachment; filename={filename}',
        'Filename': filename,
        'Content-type': 'text/json'
    }

  def _get_jobs(self, pipeline):
    job_mapping = {}
    for job in pipeline.jobs:
      job_mapping[job.id] = uuid.uuid4().hex

    jobs = []
    for job in pipeline.jobs:
      params = []
      for param in job.params:
        params.append({
            'name': param.name,
            'value': param.api_value,
            'label': param.label,
            'is_required': param.is_required,
            'type': param.type,
            'description': param.description
        })
      start_conditions = []
      for start_condition in job.start_conditions:
        start_conditions.append({
            'preceding_job_id': job_mapping[start_condition.preceding_job_id],
            'condition': start_condition.condition
        })
      jobs.append({
          'id': job_mapping[job.id],
          'name': job.name,
          'worker_class': job.worker_class,
          'params': params,
          'hash_start_conditions': start_conditions
      })
    return jobs


import_parser = reqparse.RequestParser()
import_parser.add_argument(
    'upload_file',
    type=werkzeug.datastructures.FileStorage,
    location='files'
)


class PipelineImport(Resource):
  """Class for importing of pipeline in yaml format."""

  @marshal_with(pipeline_fields)
  def post(self):
    tracker = insight.GAProvider()
    tracker.track_event(category='pipelines', action='import')

    args = import_parser.parse_args()

    file_ = args['upload_file']
    data = {}
    if file_:
      data = json.loads(file_.read())
      pipeline = models.Pipeline(name=data['name'])
      pipeline.save()
      pipeline.import_data(data)
      return pipeline, 201

    return data


class PipelineRunOnSchedule(Resource):
  """Class for starting a pipeline on a given schedule."""

  @marshal_with(pipeline_fields)
  def patch(self, pipeline_id):
    pipeline = models.Pipeline.find(pipeline_id)
    args = parser.parse_args()
    schedule_pipeline = (args['run_on_schedule'] == 'True')
    pipeline.update(run_on_schedule=schedule_pipeline)
    tracker = insight.GAProvider()
    tracker.track_event(
        category='pipelines',
        action=('schedule' if schedule_pipeline else 'unschedule'))
    return pipeline


log_parser = reqparse.RequestParser()
log_parser.add_argument('next_page_token')
log_parser.add_argument('worker_class')
log_parser.add_argument('job_id')
log_parser.add_argument('log_level')
log_parser.add_argument('query')
log_parser.add_argument('fromdate')
log_parser.add_argument('todate')

log_fields = {
    'timestamp': fields.String,
    'payload': fields.Raw,
    'job_name': fields.String
}

logs_fields = {
    'entries': fields.List(fields.Nested(log_fields)),
    'next_page_token': fields.String
}


class PipelineLogs(Resource):
  """Class for retrieving execution logs."""

  def get(self, pipeline_id):
    args = log_parser.parse_args()
    entries = []
    template_env = jinja2.Environment(loader=jinja2.BaseLoader)
    filter_template = template_env.from_string(textwrap.dedent("""\
        -jsonPayload.log_level="DEBUG"
        AND jsonPayload.labels.pipeline_id="{{ pipeline_id }}"
        {%- if worker_class %} AND jsonPayload.labels.worker_class="{{ worker_class }}"{% endif %}
        {%- if job_id %} AND jsonPayload.labels.job_id="{{ job_id }}"{% endif %}
        {%- if log_level %} AND jsonPayload.log_level="{{ log_level }}"{% endif %}
        {%- if query %} AND jsonPayload.message:"{{ query }}"{% endif %}
        {%- if fromdate %} AND timestamp>="{{ fromdate }}"{% endif %}
        {%- if todate %} AND timestamp<="{{ todate }}"{% endif %}
        {%- if next_page_token %} AND timestamp<"{{ next_page_token }}"{% endif %}
        """))
    filter_ = filter_template.render(
        pipeline_id=pipeline_id,
        worker_class=args.get('worker_class'),
        job_id=args.get('job_id'),
        log_level=args.get('log_level'),
        query=args.get('query'),
        fromdate=args.get('fromdate'),
        todate=args.get('todate'),
        next_page_token=args.get('next_page_token'))
    # NOTE: `page_size` defines the number of entries to fetch in each API call.
    #       Although requests are paged internally, logs are returned by the
    #       generator one at a time.
    #       `max_results` has to be used if we don't want the generator to
    #       exhaust our reading quota.
    list_entries_iter = crmint_logging.get_logger().list_entries(
        filter_=filter_,
        order_by=logging.DESCENDING,
        page_size=_LOGS_PAGE_SIZE,
        max_results=_LOGS_PAGE_SIZE)
    for entry in list_entries_iter:
      if not isinstance(entry.payload, dict):
        continue

      job_id = entry.payload.get('labels', {}).get('job_id')
      if not job_id:
        continue

      job = models.Job.find(job_id)
      if job:
        log = {
            'timestamp': entry.timestamp.isoformat().replace('+00:00', 'Z'),
            'payload': entry.payload,
            'job_name': job.name,
            'log_level': entry.payload.get('log_level', 'INFO'),
        }
      else:
        log = {
            'timestamp': entry.timestamp.isoformat().replace('+00:00', 'Z'),
            'payload': entry.payload,
            'job_name': 'N/A',
            'log_level': entry.payload.get('log_level', 'INFO'),
        }
      entries.append(log)
    return {'entries': entries}


api.add_resource(PipelineList, '/pipelines')
api.add_resource(PipelineSingle, '/pipelines/<pipeline_id>')
api.add_resource(PipelineStart, '/pipelines/<pipeline_id>/start')
api.add_resource(PipelineStop, '/pipelines/<pipeline_id>/stop')
api.add_resource(PipelineExport, '/pipelines/<pipeline_id>/export')
api.add_resource(PipelineImport, '/pipelines/import')
api.add_resource(
    PipelineRunOnSchedule,
    '/pipelines/<pipeline_id>/run_on_schedule'
)
api.add_resource(PipelineLogs, '/pipelines/<pipeline_id>/logs')
