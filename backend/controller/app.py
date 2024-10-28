# Copyright 2018 Google Inc
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

"""The app module, containing the app factory function."""

import os
from typing import Any, Optional
from flask import Flask

from controller import extensions
from controller import job
from controller import pipeline
from controller import result
from controller import stage
from controller import starter
from controller import views

from common import crmint_logging

def create_app(config: Optional[dict[str, Any]] = None) -> Flask:
  """An application factory.

  Args:
    config: Dictionary of config flags to update the app with.

  Returns:
    The configured Flask application.
  """
  crmint_logging.log_global_message('[app.create_app()] Entered', log_level='DEBUG')

  app = Flask(__name__)

  # Set up database connection pooling
  app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URI',
    'mysql+mysqlconnector://crmint:crmint@db:3306/crmint_development')
  app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
  app.config['SQLALCHEMY_ECHO'] = True

  if config:
    app.config.update(**config)

  crmint_logging.log_global_message('[app.create_app()] Registering extensions', log_level='DEBUG')
  register_extensions(app)

  crmint_logging.log_global_message('[app.create_app()] Registering blueprints', log_level='DEBUG')
  register_blueprints(app)

  crmint_logging.log_global_message('[app.create_app()] Exiting', log_level='DEBUG')

  return app


def register_extensions(app):
  """Register Flask extensions."""
  extensions.cors.init_app(app)
  extensions.db.init_app(app)
  extensions.migrate.init_app(app, extensions.db)


def register_blueprints(app):
  """Register Flask blueprints."""
  app.register_blueprint(views.blueprint, url_prefix='/api')
  app.register_blueprint(pipeline.views.blueprint, url_prefix='/api')
  app.register_blueprint(job.views.blueprint, url_prefix='/api')
  app.register_blueprint(stage.views.blueprint, url_prefix='/api')
  app.register_blueprint(result.views.blueprint)
  app.register_blueprint(starter.views.blueprint)
