# Copyright 2020 Google Inc
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

"""Task results handler."""

import datetime

from flask import Blueprint
from flask import request
from flask_restful import Api
from flask_restful import Resource

from common import crmint_logging
from common import insight
from common import message
from controller import cron_utils
from controller import models
from sqlalchemy import orm

blueprint = Blueprint('starter', __name__)
api = Api(blueprint)


class StarterResource(Resource):
  """Processes PubSub POST requests from crmint-start-pipeline topic."""

  def _start_scheduled_pipelines(self):
    """Finds and tries starting the pipelines scheduled to be executed now."""
    crmint_logging.log_global_message("[StarterResource._start_scheduled_pipelines()] Entered", log_level='DEBUG')
    now_dt = datetime.datetime.utcnow()

    for pipeline in models.Pipeline.where(run_on_schedule=True).all():
      for schedule in pipeline.schedules:
        cron_match_result = cron_utils.cron_match(schedule.cron, now_dt)
        if cron_match_result:
          pipeline.start()
          tracker = insight.GAProvider()
          tracker.track_event(category='pipelines', action='scheduled_run')
          break

  def _start_pipelines(self, pipeline_ids):
    """Tries finding and starting pipelines with IDs specified."""
    crmint_logging.log_global_message("[StarterResource._start_pipelines()] Entered", log_level='DEBUG')
    for pipeline_id in pipeline_ids:
      pipeline = models.Pipeline.find(pipeline_id)
      if pipeline is not None:
        pipeline.start()
        tracker = insight.GAProvider()
        tracker.track_event(category='pipelines', action='pubsub_run')

  def post(self):
    crmint_logging.log_global_message("[StarterResource.post()] Entered", log_level='DEBUG')
    try:
      data = message.extract_data(request)
      try:
        pipeline_ids = data['pipeline_ids']
      except KeyError as e:
        raise message.BadRequestError() from e
      if pipeline_ids == 'scheduled':
        self._start_scheduled_pipelines()
      elif isinstance(pipeline_ids, list):
        self._start_pipelines(pipeline_ids)
      else:
        raise message.BadRequestError()
    except message.BadRequestError as e:
      return e.message, e.code
    crmint_logging.log_global_message("[StarterResource.post()] Exiting", log_level='DEBUG')
    return 'OK', 200


api.add_resource(StarterResource, '/push/start-pipeline')
