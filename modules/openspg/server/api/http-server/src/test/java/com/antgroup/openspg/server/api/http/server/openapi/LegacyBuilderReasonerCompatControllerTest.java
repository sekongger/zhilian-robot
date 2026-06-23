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

package com.antgroup.openspg.server.api.http.server.openapi;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.antgroup.openspg.cloudext.interfaces.searchengine.model.idx.record.IdxRecord;
import com.antgroup.openspg.server.api.facade.Paged;
import com.antgroup.openspg.server.api.facade.dto.service.request.CustomSearchRequest;
import com.antgroup.openspg.server.api.facade.dto.service.request.SPGTypeSearchRequest;
import com.antgroup.openspg.server.api.facade.dto.service.request.TextSearchRequest;
import com.antgroup.openspg.server.api.facade.dto.service.request.VectorSearchRequest;
import com.antgroup.openspg.server.api.http.server.HttpResult;
import com.antgroup.openspg.server.biz.service.SearchManager;
import com.antgroup.openspg.server.common.model.bulider.BuilderJob;
import com.antgroup.openspg.server.common.model.bulider.BuilderJobQuery;
import com.antgroup.openspg.server.common.model.retrieval.Retrieval;
import com.antgroup.openspg.server.common.model.retrieval.RetrievalQuery;
import com.antgroup.openspg.server.common.service.builder.BuilderJobService;
import com.antgroup.openspg.server.common.service.retrieval.RetrievalService;
import java.lang.reflect.Field;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

public class LegacyBuilderReasonerCompatControllerTest {

  @Test
  public void resolveBuilderFileUrl_shouldExtractFromLegacyMapString() {
    LegacyBuilderReasonerCompatController controller = new LegacyBuilderReasonerCompatController();
    String raw = "{name=new1.md, fileUrl=/tmp/openspg-legacy-upload/123/new1.md, type=md}";
    String parsed = controller.resolveBuilderFileUrl(raw);
    assertEquals("/tmp/openspg-legacy-upload/123/new1.md", parsed);
  }

  @Test
  public void resolveBuilderFileUrl_shouldExtractFromMapObject() {
    LegacyBuilderReasonerCompatController controller = new LegacyBuilderReasonerCompatController();
    Map<String, Object> raw = new HashMap<>();
    raw.put("name", "new1.md");
    raw.put("fileUrl", "/tmp/openspg-legacy-upload/456/new1.md");
    String parsed = controller.resolveBuilderFileUrl(raw);
    assertEquals("/tmp/openspg-legacy-upload/456/new1.md", parsed);
  }

  @Test
  public void queryReasonerBuilder_shouldPopulateSampleSubgraph_whenRetrievalExists()
      throws Exception {
    LegacyBuilderReasonerCompatController controller = new LegacyBuilderReasonerCompatController();

    BuilderJob builderJob = new BuilderJob();
    builderJob.setId(27L);
    builderJob.setProjectId(1L);
    builderJob.setJobName("智链机器人产业头条");

    Retrieval retrieval = new Retrieval();
    retrieval.setId(3L);
    retrieval.setName("summary_index");
    retrieval.setClassName("Chunk");
    retrieval.setConfig("{\"retriever\":[{\"type\":\"summary_chunk_retriever\"}]}");

    Map<String, Object> fields = new HashMap<>();
    fields.put("title", "智链机器人完成新一轮融资");
    fields.put("content", "智链机器人宣布完成新一轮融资，将继续投入具身智能研发。");
    IdxRecord idxRecord = new IdxRecord("summary_index", "doc-1", 0.92d, fields);
    idxRecord.setLabel("Chunk");

    setField(controller, "builderJobService", new TestBuilderJobService(builderJob));
    setField(controller, "retrievalService", new TestRetrievalService(retrieval));
    setField(
        controller, "searchManager", new TestSearchManager(Collections.singletonList(idxRecord)));

    HttpResult<Map<String, Object>> httpResult = controller.queryReasonerBuilder(null, 3L, 27L);

    assertTrue(httpResult.isSuccess());
    Map<String, Object> result = httpResult.getResult();
    assertNotNull(result);
    assertEquals(3L, ((Number) result.get("id")).longValue());

    List<?> nodes = (List<?>) result.get("resultNodes");
    assertNotNull(nodes);
    assertFalse(nodes.isEmpty());
  }

  private static void setField(Object target, String fieldName, Object value) throws Exception {
    Field field = target.getClass().getDeclaredField(fieldName);
    field.setAccessible(true);
    field.set(target, value);
  }

  private static class TestBuilderJobService implements BuilderJobService {
    private final BuilderJob builderJob;

    private TestBuilderJobService(BuilderJob builderJob) {
      this.builderJob = builderJob;
    }

    @Override
    public Long insert(BuilderJob record) {
      return null;
    }

    @Override
    public int deleteById(Long id) {
      return 0;
    }

    @Override
    public Long update(BuilderJob record) {
      return null;
    }

    @Override
    public BuilderJob getById(Long id) {
      return builderJob;
    }

    @Override
    public Paged<BuilderJob> query(BuilderJobQuery record) {
      return null;
    }
  }

  private static class TestRetrievalService implements RetrievalService {
    private final Retrieval retrieval;

    private TestRetrievalService(Retrieval retrieval) {
      this.retrieval = retrieval;
    }

    @Override
    public Long insert(Retrieval record) {
      return null;
    }

    @Override
    public int deleteById(Long id) {
      return 0;
    }

    @Override
    public Long update(Retrieval record) {
      return null;
    }

    @Override
    public Retrieval getById(Long id) {
      return retrieval;
    }

    @Override
    public Retrieval getByName(String name) {
      return retrieval;
    }

    @Override
    public Paged<Retrieval> query(RetrievalQuery record) {
      return null;
    }

    @Override
    public List<Retrieval> getRetrievalByProjectId(Long projectId) {
      return Collections.singletonList(retrieval);
    }
  }

  private static class TestSearchManager implements SearchManager {
    private final List<IdxRecord> records;

    private TestSearchManager(List<IdxRecord> records) {
      this.records = records;
    }

    @Override
    public List<IdxRecord> spgTypeSearch(SPGTypeSearchRequest request) {
      return records;
    }

    @Override
    public List<IdxRecord> textSearch(TextSearchRequest request) {
      return records;
    }

    @Override
    public List<IdxRecord> vectorSearch(VectorSearchRequest request) {
      return records;
    }

    @Override
    public List<IdxRecord> customSearch(CustomSearchRequest request) {
      return records;
    }
  }
}
