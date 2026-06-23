/*
 * Copyright 2023 OpenSPG Authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied.
 */

package com.antgroup.openspg.cloudext.impl.computingengine.local;

public class LocalComputingEngineConstants {

  public static final String DRIVER_SCHEME = "local";
  public static final String WORK_DIR = "workDir";
  public static final String WORK_DIR_DEFAULT = "/tmp/openspg-computing-local";

  public static final String COMMAND = "command";
  public static final String ENVS = "envs";

  public static final String TASK_ID_ENV = "OPENSPG_COMPUTING_TASK_ID";
  public static final String JOB_ID_ENV = "OPENSPG_COMPUTING_JOB_ID";
  public static final String PROJECT_ID_ENV = "OPENSPG_COMPUTING_PROJECT_ID";

  public static final long STOP_WAIT_MILLIS = 3000L;
  public static final long TERMINAL_TASK_RETENTION_MILLIS = 24L * 60L * 60L * 1000L;

  private LocalComputingEngineConstants() {}
}
