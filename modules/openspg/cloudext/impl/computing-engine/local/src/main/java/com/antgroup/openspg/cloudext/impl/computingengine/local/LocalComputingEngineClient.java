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

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;
import com.antgroup.openspg.cloudext.interfaces.computingengine.ComputingEngineClient;
import com.antgroup.openspg.cloudext.interfaces.computingengine.model.ComputingStatusEnum;
import com.antgroup.openspg.cloudext.interfaces.computingengine.model.ComputingTask;
import com.antgroup.openspg.server.common.model.bulider.BuilderJob;
import java.io.File;
import java.io.IOException;
import java.io.UnsupportedEncodingException;
import java.net.URI;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import lombok.Getter;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;

@Slf4j
public class LocalComputingEngineClient implements ComputingEngineClient<JSONObject> {

  private static final String LOCAL_SHELL = "/bin/sh";
  private static final ConcurrentHashMap<String, TaskRuntime> TASK_REGISTRY =
      new ConcurrentHashMap<>();

  @Getter private final String connUrl;
  @Getter private final Path workDir;

  public LocalComputingEngineClient(String connUrl) {
    this.connUrl = connUrl;
    this.workDir = resolveWorkDir(connUrl);
    ensureDirectory(this.workDir);
  }

  @Override
  public ComputingTask submitBuilderJob(BuilderJob builderJob, JSONObject extension) {
    String command =
        (extension == null) ? null : extension.getString(LocalComputingEngineConstants.COMMAND);
    if (StringUtils.isBlank(command)) {
      throw new IllegalArgumentException("local computing engine requires non-empty command");
    }

    cleanupTaskRegistry();
    String taskId = UUID.randomUUID().toString().replace("-", "");
    Path logFile = workDir.resolve(taskId + ".log");
    Process process = startProcess(command, extension, builderJob, taskId, logFile);
    TASK_REGISTRY.put(
        taskId, new TaskRuntime(taskId, process, logFile.toString(), System.currentTimeMillis()));

    ComputingTask task = new ComputingTask();
    task.setTaskId(taskId);
    task.setLogUrl(logFile.toString());
    return task;
  }

  @Override
  public ComputingStatusEnum queryStatus(JSONObject extension, String id) {
    TaskRuntime runtime = TASK_REGISTRY.get(id);
    if (runtime == null) {
      return ComputingStatusEnum.NOTFOUND;
    }
    if (runtime.stopRequested.get()) {
      return ComputingStatusEnum.STOP;
    }
    Process process = runtime.process;
    if (process != null && process.isAlive()) {
      return ComputingStatusEnum.RUNNING;
    }
    if (process == null) {
      return ComputingStatusEnum.UNDEFINED;
    }
    int exitCode = process.exitValue();
    return exitCode == 0 ? ComputingStatusEnum.SUCCESS : ComputingStatusEnum.FAILED;
  }

  @Override
  public Boolean stop(JSONObject extension, String id) {
    TaskRuntime runtime = TASK_REGISTRY.get(id);
    if (runtime == null) {
      return false;
    }

    runtime.stopRequested.set(true);
    Process process = runtime.process;
    if (process == null) {
      return true;
    }

    if (!process.isAlive()) {
      return true;
    }
    process.destroy();
    try {
      boolean finished =
          process.waitFor(LocalComputingEngineConstants.STOP_WAIT_MILLIS, TimeUnit.MILLISECONDS);
      if (!finished && process.isAlive()) {
        process.destroyForcibly();
      }
    } catch (InterruptedException e) {
      Thread.currentThread().interrupt();
      process.destroyForcibly();
    }
    return true;
  }

  private Process startProcess(
      String command, JSONObject extension, BuilderJob builderJob, String taskId, Path logFile) {
    try {
      ensureDirectory(logFile.getParent());
      ProcessBuilder builder = new ProcessBuilder(LOCAL_SHELL, "-lc", command);
      builder.redirectErrorStream(true);
      builder.redirectOutput(ProcessBuilder.Redirect.appendTo(logFile.toFile()));
      builder.directory(new File(workDir.toAbsolutePath().toString()));

      Map<String, String> env = builder.environment();
      env.put(LocalComputingEngineConstants.TASK_ID_ENV, taskId);
      if (builderJob != null) {
        if (builderJob.getId() != null) {
          env.put(LocalComputingEngineConstants.JOB_ID_ENV, String.valueOf(builderJob.getId()));
        }
        if (builderJob.getProjectId() != null) {
          env.put(
              LocalComputingEngineConstants.PROJECT_ID_ENV,
              String.valueOf(builderJob.getProjectId()));
        }
      }
      env.putAll(parseExtensionEnvs(extension));
      return builder.start();
    } catch (IOException e) {
      throw new RuntimeException("local computing engine failed to start command: " + command, e);
    }
  }

  private static Path resolveWorkDir(String connUrl) {
    String fromUrl = getQueryParam(connUrl, LocalComputingEngineConstants.WORK_DIR);
    String candidate =
        StringUtils.isBlank(fromUrl)
            ? LocalComputingEngineConstants.WORK_DIR_DEFAULT
            : fromUrl.trim();
    return Paths.get(candidate).toAbsolutePath().normalize();
  }

  private static String getQueryParam(String connUrl, String key) {
    if (StringUtils.isBlank(connUrl)) {
      return null;
    }
    try {
      URI uri = URI.create(connUrl);
      String query = uri.getRawQuery();
      if (StringUtils.isBlank(query)) {
        return null;
      }
      String[] pairs = query.split("&");
      for (String pair : pairs) {
        String[] kv = pair.split("=", 2);
        if (kv.length == 0) {
          continue;
        }
        String k = decodeUrlPart(kv[0]);
        if (!key.equals(k)) {
          continue;
        }
        return kv.length > 1 ? decodeUrlPart(kv[1]) : "";
      }
      return null;
    } catch (Exception e) {
      log.warn("parse local computing engine connUrl failed: {}", connUrl, e);
      return null;
    }
  }

  private static String decodeUrlPart(String value) throws UnsupportedEncodingException {
    return URLDecoder.decode(value, StandardCharsets.UTF_8.name());
  }

  private static Map<String, String> parseExtensionEnvs(JSONObject extension) {
    if (extension == null || !extension.containsKey(LocalComputingEngineConstants.ENVS)) {
      return Collections.emptyMap();
    }

    Object envObject = extension.get(LocalComputingEngineConstants.ENVS);
    Map<String, String> envs = new LinkedHashMap<>();
    if (envObject instanceof Map) {
      putMapAsString(envs, (Map<?, ?>) envObject);
      return envs;
    }
    if (envObject instanceof String && StringUtils.isNotBlank((String) envObject)) {
      try {
        JSONObject envJson = JSON.parseObject((String) envObject);
        putMapAsString(envs, envJson);
      } catch (Exception e) {
        log.warn("parse local computing envs string failed: {}", envObject, e);
      }
    }
    return envs;
  }

  private static void putMapAsString(Map<String, String> target, Map<?, ?> source) {
    for (Map.Entry<?, ?> entry : source.entrySet()) {
      if (entry.getKey() == null || entry.getValue() == null) {
        continue;
      }
      target.put(String.valueOf(entry.getKey()), String.valueOf(entry.getValue()));
    }
  }

  private static void ensureDirectory(Path path) {
    if (path == null) {
      return;
    }
    try {
      Files.createDirectories(path);
    } catch (IOException e) {
      throw new RuntimeException("create local computing work dir failed: " + path, e);
    }
  }

  private static void cleanupTaskRegistry() {
    long now = System.currentTimeMillis();
    TASK_REGISTRY
        .entrySet()
        .removeIf(
            entry -> {
              TaskRuntime runtime = entry.getValue();
              if (runtime == null || runtime.process == null) {
                return true;
              }
              boolean terminal = !runtime.process.isAlive();
              return terminal
                  && now - runtime.submitAtMillis
                      > LocalComputingEngineConstants.TERMINAL_TASK_RETENTION_MILLIS;
            });
  }

  private static class TaskRuntime {

    private final String taskId;
    private final Process process;
    private final String logPath;
    private final long submitAtMillis;
    private final AtomicBoolean stopRequested = new AtomicBoolean(false);

    private TaskRuntime(String taskId, Process process, String logPath, long submitAtMillis) {
      this.taskId = taskId;
      this.process = process;
      this.logPath = logPath;
      this.submitAtMillis = submitAtMillis;
    }
  }
}
