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

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONObject;
import com.antgroup.openspg.cloudext.interfaces.searchengine.model.idx.record.IdxRecord;
import com.antgroup.openspg.common.util.StringUtils;
import com.antgroup.openspg.server.api.facade.Paged;
import com.antgroup.openspg.server.api.facade.dto.service.request.TextSearchRequest;
import com.antgroup.openspg.server.api.http.server.BaseController;
import com.antgroup.openspg.server.api.http.server.HttpBizCallback;
import com.antgroup.openspg.server.api.http.server.HttpBizTemplate;
import com.antgroup.openspg.server.api.http.server.HttpResult;
import com.antgroup.openspg.server.biz.common.util.AssertUtils;
import com.antgroup.openspg.server.biz.service.SearchManager;
import com.antgroup.openspg.server.common.model.bulider.BuilderJob;
import com.antgroup.openspg.server.common.model.bulider.BuilderJobQuery;
import com.antgroup.openspg.server.common.model.retrieval.Retrieval;
import com.antgroup.openspg.server.common.model.retrieval.RetrievalQuery;
import com.antgroup.openspg.server.common.model.scheduler.SchedulerEnum;
import com.antgroup.openspg.server.common.service.builder.BuilderJobService;
import com.antgroup.openspg.server.common.service.retrieval.RetrievalService;
import java.util.ArrayList;
import java.util.Date;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.ResponseBody;

@Controller
@RequestMapping("/public/v1/retrieval")
@Slf4j
public class RetrievalController extends BaseController {

  @Autowired private RetrievalService retrievalService;

  @Autowired private BuilderJobService builderJobService;

  @Autowired private SearchManager searchManager;

  @RequestMapping(value = "/getAll", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<List<Retrieval>> getAll() {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<List<Retrieval>>() {
          @Override
          public void check() {
            log.info("/retrieval/getAll");
          }

          @Override
          public List<Retrieval> action() {
            List<Retrieval> retrievals = retrievalService.query(new RetrievalQuery()).getResults();
            if (retrievals != null && !retrievals.isEmpty()) {
              return retrievals;
            }
            BuilderJobQuery query = new BuilderJobQuery();
            query.setPageNo(1);
            query.setPageSize(200);
            Paged<BuilderJob> paged = builderJobService.query(query);
            List<BuilderJob> jobs =
                paged == null || paged.getResults() == null
                    ? new ArrayList<>()
                    : paged.getResults();
            Set<Long> projectIds = new LinkedHashSet<>();
            for (BuilderJob job : jobs) {
              if (job != null && job.getProjectId() != null) {
                projectIds.add(job.getProjectId());
              }
            }
            List<Retrieval> fallback = new ArrayList<>();
            for (Long projectId : projectIds) {
              fallback.addAll(buildFallbackRetrievals(projectId));
            }
            return fallback;
          }
        });
  }

  @RequestMapping(value = "/delete", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<Boolean> delete(Long id) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Boolean>() {
          @Override
          public void check() {
            log.info("/retrieval/delete id: {}", id);
            AssertUtils.assertParamObjectIsNotNull("id", id);
          }

          @Override
          public Boolean action() {
            return retrievalService.deleteById(id) > 0;
          }
        });
  }

  @RequestMapping(value = "/getById", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<Retrieval> getById(Long id) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Retrieval>() {
          @Override
          public void check() {
            log.info("/retrieval/getById id: {}", id);
            AssertUtils.assertParamObjectIsNotNull("id", id);
          }

          @Override
          public Retrieval action() {
            return retrievalService.getById(id);
          }
        });
  }

  @RequestMapping(value = "/getByProjectId", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<List<Retrieval>> getByProjectId(Long projectId) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<List<Retrieval>>() {
          @Override
          public void check() {
            log.info("/retrieval/getByProjectId projectId: {}", projectId);
            AssertUtils.assertParamObjectIsNotNull("projectId", projectId);
          }

          @Override
          public List<Retrieval> action() {
            List<Retrieval> retrievals = retrievalService.getRetrievalByProjectId(projectId);
            if (retrievals != null && !retrievals.isEmpty()) {
              return retrievals;
            }
            return buildFallbackRetrievals(projectId);
          }
        });
  }

  @RequestMapping(value = "/search", method = RequestMethod.POST)
  @ResponseBody
  public HttpResult<Paged<Retrieval>> search(@RequestBody RetrievalQuery request) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Paged<Retrieval>>() {
          @Override
          public void check() {
            log.info("/retrieval/search request: {}", JSON.toJSONString(request));
          }

          @Override
          public Paged<Retrieval> action() {
            return retrievalService.query(request);
          }
        });
  }

  @RequestMapping(value = "/update", method = RequestMethod.POST)
  @ResponseBody
  public HttpResult<Long> update(@RequestBody Retrieval request) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Long>() {
          @Override
          public void check() {
            log.info("/retrieval/update request: {}", JSON.toJSONString(request));
            AssertUtils.assertParamObjectIsNotNull("retrieval", request);
            AssertUtils.assertParamObjectIsNotNull("id", request.getId());
          }

          @Override
          public Long action() {
            return retrievalService.update(request);
          }
        });
  }

  private List<Retrieval> buildFallbackRetrievals(Long projectId) {
    List<Retrieval> result = new ArrayList<>();
    if (projectId == null) {
      return result;
    }

    Date now = new Date();
    result.add(buildFallbackRetrieval(projectId, "__ALL__", "全量索引", "all", now, 0, "legacy-all"));

    Set<String> labels = discoverLabels(projectId);
    int order = 1;
    for (String label : labels) {
      result.add(buildFallbackRetrieval(projectId, label, label, label, now, order++, label));
    }
    return result;
  }

  private Set<String> discoverLabels(Long projectId) {
    Set<String> labels = new LinkedHashSet<>();
    try {
      TextSearchRequest request = new TextSearchRequest();
      request.setProjectId(projectId);
      request.setQueryString("*");
      request.setPage(1);
      request.setTopk(100);
      List<IdxRecord> records = searchManager.textSearch(request);
      if (records == null) {
        return labels;
      }
      for (IdxRecord record : records) {
        if (record != null && StringUtils.isNotBlank(record.getLabel())) {
          labels.add(record.getLabel());
        }
      }
    } catch (Exception ex) {
      log.warn("discover labels failed, projectId={}", projectId, ex);
    }
    return labels;
  }

  private Retrieval buildFallbackRetrieval(
      Long projectId,
      String name,
      String chineseName,
      String className,
      Date now,
      int order,
      String configLabel) {
    Retrieval retrieval = new Retrieval();
    retrieval.setId(buildFallbackRetrievalId(projectId, name, order));
    retrieval.setName(name);
    retrieval.setChineseName(chineseName);
    retrieval.setClassName(className);
    retrieval.setType("TEXT_SEARCH");
    retrieval.setStatus(SchedulerEnum.Status.ENABLE.name());
    retrieval.setCreateUser("openspg");
    retrieval.setUpdateUser("openspg");
    retrieval.setGmtCreate(now);
    retrieval.setGmtModified(now);
    JSONObject config = new JSONObject();
    config.put("projectId", projectId);
    config.put("label", configLabel);
    config.put("source", "legacy-fallback");
    retrieval.setConfig(config.toJSONString());
    return retrieval;
  }

  private Long buildFallbackRetrievalId(Long projectId, String name, int order) {
    String seed = String.valueOf(projectId) + ":" + String.valueOf(name) + ":" + order;
    long hash = Math.abs(seed.hashCode());
    return 9000000000L + hash;
  }
}
