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

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.alibaba.fastjson.JSONObject;
import com.antgroup.openspg.cloudext.interfaces.computingengine.model.ComputingStatusEnum;
import com.antgroup.openspg.cloudext.interfaces.computingengine.model.ComputingTask;
import com.antgroup.openspg.server.common.model.bulider.BuilderJob;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

public class LocalComputingEngineClientTest {

  private Path tempDir;

  @AfterEach
  public void tearDown() throws IOException {
    if (tempDir == null || !Files.exists(tempDir)) {
      return;
    }
    Files.walk(tempDir)
        .sorted((left, right) -> right.getNameCount() - left.getNameCount())
        .forEach(
            path -> {
              try {
                Files.deleteIfExists(path);
              } catch (IOException ignored) {
                // ignore in unit test cleanup
              }
            });
  }

  @Test
  public void testSubmitBuilderJobSuccessWithEnv() throws Exception {
    LocalComputingEngineClient client = createClient();
    JSONObject extension = new JSONObject();
    extension.put("command", "[ \"$TEST_LOCAL_ENV\" = \"ok\" ]");
    JSONObject envs = new JSONObject();
    envs.put("TEST_LOCAL_ENV", "ok");
    extension.put("envs", envs);

    ComputingTask task = client.submitBuilderJob(newBuilderJob(), extension);
    assertNotNull(task.getTaskId());
    assertTrue(task.getLogUrl().contains(task.getTaskId()));

    ComputingStatusEnum status = waitTerminalStatus(client, task.getTaskId(), 5000L);
    assertEquals(ComputingStatusEnum.SUCCESS, status);
  }

  @Test
  public void testSubmitBuilderJobFailed() throws Exception {
    LocalComputingEngineClient client = createClient();
    JSONObject extension = new JSONObject();
    extension.put("command", "exit 9");

    ComputingTask task = client.submitBuilderJob(newBuilderJob(), extension);
    ComputingStatusEnum status = waitTerminalStatus(client, task.getTaskId(), 5000L);
    assertEquals(ComputingStatusEnum.FAILED, status);
  }

  @Test
  public void testStopRunningTask() throws Exception {
    LocalComputingEngineClient client = createClient();
    JSONObject extension = new JSONObject();
    extension.put("command", "sleep 10");

    ComputingTask task = client.submitBuilderJob(newBuilderJob(), extension);
    assertTrue(client.stop(new JSONObject(), task.getTaskId()));

    ComputingStatusEnum status = waitTerminalStatus(client, task.getTaskId(), 5000L);
    assertEquals(ComputingStatusEnum.STOP, status);
  }

  @Test
  public void testSubmitBuilderJobRejectBlankCommand() throws Exception {
    LocalComputingEngineClient client = createClient();
    assertThrows(
        IllegalArgumentException.class,
        () -> client.submitBuilderJob(newBuilderJob(), new JSONObject()));
  }

  private LocalComputingEngineClient createClient() throws IOException {
    tempDir = Files.createTempDirectory("openspg-local-computing-test");
    String connUrl = "local://localhost?workDir=" + tempDir.toAbsolutePath();
    return new LocalComputingEngineClient(connUrl);
  }

  private BuilderJob newBuilderJob() {
    BuilderJob job = new BuilderJob();
    job.setId(1L);
    job.setProjectId(1L);
    return job;
  }

  private ComputingStatusEnum waitTerminalStatus(
      LocalComputingEngineClient client, String taskId, long timeoutMillis)
      throws InterruptedException {
    long end = System.currentTimeMillis() + timeoutMillis;
    while (System.currentTimeMillis() < end) {
      ComputingStatusEnum status = client.queryStatus(new JSONObject(), taskId);
      if (status == ComputingStatusEnum.RUNNING || status == ComputingStatusEnum.SUBMIT) {
        Thread.sleep(100L);
        continue;
      }
      return status;
    }
    return client.queryStatus(new JSONObject(), taskId);
  }
}
