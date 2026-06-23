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
import com.antgroup.openspg.common.constants.BuilderConstant;
import com.antgroup.openspg.common.util.DateTimeUtils;
import com.antgroup.openspg.common.util.StringUtils;
import com.antgroup.openspg.server.api.facade.Paged;
import com.antgroup.openspg.server.api.facade.dto.common.request.ProjectQueryRequest;
import com.antgroup.openspg.server.api.facade.dto.service.request.TextSearchRequest;
import com.antgroup.openspg.server.api.http.server.BaseController;
import com.antgroup.openspg.server.api.http.server.HttpBizCallback;
import com.antgroup.openspg.server.api.http.server.HttpBizTemplate;
import com.antgroup.openspg.server.api.http.server.HttpResult;
import com.antgroup.openspg.server.biz.common.ProjectManager;
import com.antgroup.openspg.server.biz.service.SearchManager;
import com.antgroup.openspg.server.common.model.account.Account;
import com.antgroup.openspg.server.common.model.bulider.BuilderJob;
import com.antgroup.openspg.server.common.model.bulider.BuilderJobQuery;
import com.antgroup.openspg.server.common.model.project.Project;
import com.antgroup.openspg.server.common.model.retrieval.Retrieval;
import com.antgroup.openspg.server.common.model.scheduler.SchedulerEnum;
import com.antgroup.openspg.server.common.service.builder.BuilderJobService;
import com.antgroup.openspg.server.common.service.retrieval.RetrievalService;
import com.antgroup.openspg.server.core.scheduler.model.service.SchedulerJob;
import com.antgroup.openspg.server.core.scheduler.service.api.SchedulerService;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.GZIPInputStream;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.multipart.MultipartFile;

/** Legacy `/public/v1/*` endpoints used by old console pages. */
@Controller
@RequestMapping("/public/v1")
@Slf4j
public class LegacyBuilderReasonerCompatController extends BaseController {

  private static final String LEGACY_UPLOAD_ROOT =
      System.getProperty("java.io.tmpdir") + File.separator + "openspg-legacy-upload";

  private static final Pattern LEGACY_FILE_URL_PATTERN =
      Pattern.compile("(?:^|[\\{,\\s])fileUrl=([^,}]+)");

  private static final Pattern LEGACY_URL_PATTERN = Pattern.compile("(?:^|[\\{,\\s])url=([^,}]+)");
  private static final Pattern COMPANY_CANDIDATE_PATTERN =
      Pattern.compile(
          "([\\u4e00-\\u9fa5A-Za-z0-9·()（）]{2,80}(?:股份有限公司|有限责任公司|科技股份公司|科技有限公司|集团|公司|有限公司|银行|证券|保险))");

  private static final AtomicLong SESSION_ID_ALLOCATOR = new AtomicLong(1000L);
  private static final AtomicLong REASONER_TASK_ID_ALLOCATOR = new AtomicLong(100000L);
  private static final Map<Long, Map<String, Object>> REASONER_SESSION_STORE =
      new ConcurrentHashMap<>();
  private static final Map<Long, List<Map<String, Object>>> REASONER_TASK_STORE =
      new ConcurrentHashMap<>();

  @Autowired private BuilderJobService builderJobService;

  @Autowired private RetrievalService retrievalService;

  @Autowired private SchedulerService schedulerService;

  @Autowired private ProjectManager projectManager;

  @Autowired private SearchManager searchManager;

  @RequestMapping(value = "/builder/job/list", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<Object> listBuilderJob(
      @RequestParam(required = false) Long projectId,
      @RequestParam(required = false) Long start,
      @RequestParam(required = false) Integer limit,
      @RequestParam(required = false) String keyword,
      @RequestParam(required = false) String mark,
      @RequestParam(required = false) String sort,
      @RequestParam(required = false) String order) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Object>() {
          @Override
          public void check() {}

          @Override
          public Object action() {
            int pageNo = safePageNo(start);
            int pageSize = safePageSize(limit);

            BuilderJobQuery query = new BuilderJobQuery();
            query.setProjectId(projectId);
            query.setKeyword(keyword);
            query.setSort(sort);
            query.setOrder(order);
            query.setPageNo(pageNo);
            query.setPageSize(pageSize);

            Paged<BuilderJob> paged = builderJobService.query(query);
            List<BuilderJob> data =
                paged == null || paged.getResults() == null
                    ? new ArrayList<>()
                    : paged.getResults();

            if (StringUtils.isNotBlank(mark)) {
              return data;
            }

            Map<String, Object> result = new HashMap<>();
            result.put("data", data);
            result.put("results", data);
            result.put("total", paged == null || paged.getTotal() == null ? 0L : paged.getTotal());
            result.put("pageNo", pageNo);
            result.put("pageSize", pageSize);
            result.put("start", pageNo);
            result.put("limit", pageSize);
            return result;
          }
        });
  }

  @RequestMapping(value = "/builder/job/submit", method = RequestMethod.POST)
  @ResponseBody
  public HttpResult<BuilderJob> submitBuilderJob(
      @RequestBody(required = false) Map<String, Object> body) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<BuilderJob>() {
          @Override
          public void check() {}

          @Override
          public BuilderJob action() {
            Map<String, Object> payload = body == null ? new HashMap<>() : body;
            Long projectId = normalizeProjectId(toLong(payload.get("projectId")));
            String currentUserNo = getCurrentUserNo();
            String userNo = firstNonBlank(toStr(payload.get("createUser")), currentUserNo);
            String jobName =
                firstNonBlank(
                    toStr(payload.get("jobName")),
                    "LEGACY_BUILDER_"
                        + DateTimeUtils.getDate2Str(
                            DateTimeUtils.YYYY_MM_DD_HH_MM_SS2, new Date()));
            String jobType = firstNonBlank(toStr(payload.get("type")), BuilderConstant.KAG_COMMAND);
            String lifeCycle =
                firstNonBlank(toStr(payload.get("lifeCycle")), SchedulerEnum.LifeCycle.ONCE.name());
            String dependence =
                firstNonBlank(
                    toStr(payload.get("dependence")), SchedulerEnum.Dependence.INDEPENDENT.name());

            BuilderJob job = new BuilderJob();
            job.setProjectId(projectId);
            job.setCreateUser(userNo);
            job.setModifyUser(userNo);
            job.setGmtCreate(new Date());
            job.setGmtModified(new Date());
            job.setJobName(jobName);
            job.setFileUrl(firstNonBlank(resolveBuilderFileUrl(payload.get("fileUrl")), ""));
            job.setStatus("RUNNING");
            job.setDataSourceType(firstNonBlank(toStr(payload.get("dataSourceType")), "KAG"));
            job.setType(jobType);
            job.setExtension(toNullableStr(payload.get("extension")));
            job.setVersion(
                firstNonBlank(toStr(payload.get("version")), BuilderConstant.DEFAULT_VERSION));
            job.setCron(toNullableStr(payload.get("cron")));
            job.setLifeCycle(lifeCycle);
            job.setAction(toNullableStr(payload.get("action")));
            job.setDependence(dependence);
            job.setRetrievals(toNullableStr(payload.get("retrievals")));
            job.setComputingConf(resolveComputingConf(payload));

            Long id = builderJobService.insert(job);
            job.setId(id);

            try {
              SchedulerJob schedulerJob = createSchedulerJob(job);
              BuilderJob update = new BuilderJob();
              update.setId(id);
              update.setTaskId(schedulerJob.getId());
              builderJobService.update(update);
              job.setTaskId(schedulerJob.getId());
            } catch (Exception ex) {
              log.warn("legacy builder submit create scheduler failed, jobId={}", id, ex);
            }
            return job;
          }
        });
  }

  @RequestMapping(value = "/builder/job/schema/diff", method = RequestMethod.POST)
  @ResponseBody
  public HttpResult<Map<String, Object>> schemaDiff(
      @RequestBody(required = false) Map<String, Object> body) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Map<String, Object>>() {
          @Override
          public void check() {}

          @Override
          public Map<String, Object> action() {
            Map<String, Object> result = new HashMap<>();
            result.put("entityTypeDTOList", new ArrayList<>());
            result.put("relationTypeDTOList", new ArrayList<>());
            return result;
          }
        });
  }

  @RequestMapping(value = "/builder/job/split/preview", method = RequestMethod.POST)
  @ResponseBody
  public HttpResult<Map<String, Object>> splitPreview(
      @RequestBody(required = false) Map<String, Object> body) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Map<String, Object>>() {
          @Override
          public void check() {}

          @Override
          public Map<String, Object> action() {
            Map<String, Object> result = new HashMap<>();
            result.put("splitList", new ArrayList<>());
            result.put("segments", new ArrayList<>());
            result.put("preview", "");
            return result;
          }
        });
  }

  @RequestMapping(value = "/builder/job/get", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<BuilderJob> getBuilderJob(@RequestParam Long id) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<BuilderJob>() {
          @Override
          public void check() {}

          @Override
          public BuilderJob action() {
            return builderJobService.getById(id);
          }
        });
  }

  @RequestMapping(value = "/builder/job/delete", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<Boolean> deleteBuilderJob(@RequestParam Long id) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Boolean>() {
          @Override
          public void check() {}

          @Override
          public Boolean action() {
            return builderJobService.deleteById(id) > 0;
          }
        });
  }

  @RequestMapping(value = "/reasoner/task/list", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<List<Map<String, Object>>> listReasonerTask(
      @RequestParam(required = false) Long projectId,
      @RequestParam(required = false) Integer sessionId,
      @RequestParam(required = false) Long start,
      @RequestParam(required = false) Integer limit,
      @RequestParam(required = false) String keyword,
      @RequestParam(required = false) String mark) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<List<Map<String, Object>>>() {
          @Override
          public void check() {}

          @Override
          public List<Map<String, Object>> action() {
            List<Map<String, Object>> result = new ArrayList<>();
            if (projectId == null) {
              return result;
            }

            int pageNo = safePageNo(start);
            int pageSize = safePageSize(limit);

            List<Map<String, Object>> storedTasks = listStoredReasonerTasks(projectId, keyword);
            if (!storedTasks.isEmpty()) {
              return paginate(storedTasks, pageNo, pageSize);
            }

            List<Retrieval> retrievals = resolveProjectRetrievals(projectId);
            for (Retrieval retrieval : retrievals) {
              result.add(
                  toReasonerTaskRowFromRetrieval(projectId, sessionId, keyword, mark, retrieval));
            }
            if (!result.isEmpty()) {
              return paginate(result, pageNo, pageSize);
            }

            BuilderJobQuery builderQuery = new BuilderJobQuery();
            builderQuery.setProjectId(projectId);
            builderQuery.setKeyword(keyword);
            builderQuery.setPageNo(1);
            builderQuery.setPageSize(100);
            Paged<BuilderJob> builderPaged = builderJobService.query(builderQuery);
            List<BuilderJob> jobs =
                builderPaged == null || builderPaged.getResults() == null
                    ? new ArrayList<>()
                    : builderPaged.getResults();

            for (BuilderJob job : jobs) {
              result.add(toReasonerTaskRowFromBuilder(projectId, sessionId, keyword, mark, job));
            }
            return paginate(result, pageNo, pageSize);
          }
        });
  }

  @RequestMapping(value = "/reasoner/task/builder/query", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<Map<String, Object>> queryReasonerBuilder(
      @RequestParam(required = false) Long projectId,
      @RequestParam(required = false) Long id,
      @RequestParam(required = false) Long jobId) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Map<String, Object>>() {
          @Override
          public void check() {}

          @Override
          public Map<String, Object> action() {
            Map<String, Object> result = defaultBuilderQueryResult();
            Long retrievalId = id == null ? jobId : id;
            BuilderJob builderJob = null;
            Long resolvedProjectId = projectId;
            if (jobId != null) {
              builderJob = builderJobService.getById(jobId);
              if (resolvedProjectId == null && builderJob != null) {
                resolvedProjectId = builderJob.getProjectId();
              }
            }
            if (resolvedProjectId == null && retrievalId == null) {
              return result;
            }
            Retrieval selectedRetrieval = null;
            if (projectId != null) {
              List<Retrieval> retrievals = retrievalService.getRetrievalByProjectId(projectId);
              if (retrievals != null && !retrievals.isEmpty()) {
                Retrieval first = retrievals.get(0);
                fillBuilderQueryResult(result, first);
                selectedRetrieval = first;
              }
            } else if (retrievalId != null) {
              Retrieval retrieval = retrievalService.getById(retrievalId);
              if (retrieval != null) {
                fillBuilderQueryResult(result, retrieval);
                selectedRetrieval = retrieval;
              }
            }
            if (selectedRetrieval == null && resolvedProjectId != null) {
              List<Retrieval> fallbackRetrievals = resolveProjectRetrievals(resolvedProjectId);
              if (fallbackRetrievals != null && !fallbackRetrievals.isEmpty()) {
                selectedRetrieval = fallbackRetrievals.get(0);
                fillBuilderQueryResult(result, selectedRetrieval);
              }
            }
            fillBuilderQuerySampleResult(result, resolvedProjectId, selectedRetrieval, builderJob);
            return result;
          }
        });
  }

  @RequestMapping(value = "/reasoner/dialog/retrieval", method = RequestMethod.POST)
  @ResponseBody
  public HttpResult<Map<String, Object>> reasonerDialogRetrieval(
      @RequestBody(required = false) Map<String, Object> body) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Map<String, Object>>() {
          @Override
          public void check() {}

          @Override
          public Map<String, Object> action() {
            Map<String, Object> request = body == null ? new HashMap<>() : body;
            Long projectId = normalizeProjectId(toLong(request.get("projectId")));
            Long sessionId = toLong(request.get("sessionId"));
            String instruction =
                firstNonBlank(toStr(request.get("instruction")), toStr(request.get("queryText")));
            instruction = StringUtils.isBlank(instruction) ? "*" : instruction.trim();

            List<Retrieval> retrievalOptions = resolveProjectRetrievals(projectId);
            List<Retrieval> selectedRetrievals =
                resolveSelectedRetrievals(
                    retrievalOptions, parseLongList(request.get("retrievals")));
            Set<String> labelConstraints = resolveLabelConstraints(selectedRetrievals);

            List<IdxRecord> records =
                searchTextRecords(projectId, instruction, labelConstraints, 8, true);
            List<Map<String, Object>> referenceInfo = buildReferenceInfo(records);
            List<String> callbackSegmentation = buildCallbackSegmentation(referenceInfo);
            List<Map<String, Object>> subgraphs = buildSubgraphs(records, selectedRetrievals);

            Map<String, Object> payload = new HashMap<>();
            payload.put(
                "reference",
                Collections.singletonList(Collections.singletonMap("info", referenceInfo)));
            payload.put("callbackSegmentation", callbackSegmentation);
            payload.put("subgraph", subgraphs);

            long taskId = REASONER_TASK_ID_ALLOCATOR.incrementAndGet();
            String resultMessage = JSON.toJSONString(payload);
            saveReasonerTask(
                taskId,
                projectId,
                sessionId,
                instruction,
                selectedRetrievals,
                resultMessage,
                request);

            Map<String, Object> result = new HashMap<>();
            result.put("id", taskId);
            result.put("status", "FINISH");
            result.put("resultMessage", resultMessage);
            result.put("request", request);
            return result;
          }
        });
  }

  @RequestMapping(value = "/reasoner/dialog/uploadFile", method = RequestMethod.POST)
  @ResponseBody
  public HttpResult<Map<String, Object>> reasonerDialogUploadFile(
      @RequestParam(required = false) MultipartFile file,
      @RequestParam(required = false) String type) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Map<String, Object>>() {
          @Override
          public void check() {}

          @Override
          public Map<String, Object> action() {
            String fileName =
                file == null
                    ? "legacy-upload.bin"
                    : firstNonBlank(file.getOriginalFilename(), "legacy-upload.bin");
            String fileUrl =
                file == null
                    ? LEGACY_UPLOAD_ROOT
                        + File.separator
                        + System.currentTimeMillis()
                        + File.separator
                        + fileName
                    : saveLegacyUploadFile(file, fileName);
            Map<String, Object> result = new HashMap<>();
            result.put("name", fileName);
            result.put("url", fileUrl);
            result.put("fileUrl", fileUrl);
            result.put("type", type);
            return result;
          }
        });
  }

  @RequestMapping(value = "/reasoner/session/list", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<List<Map<String, Object>>> listReasonerSession(
      @RequestParam(required = false) Long start,
      @RequestParam(required = false) Integer limit,
      @RequestParam(required = false) Integer appId,
      @RequestParam(required = false) String type) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<List<Map<String, Object>>>() {
          @Override
          public void check() {}

          @Override
          public List<Map<String, Object>> action() {
            List<Map<String, Object>> sessions = new ArrayList<>(REASONER_SESSION_STORE.values());
            sessions.sort(
                (a, b) ->
                    Long.compare(
                        toLong(b.get("id")) == null ? 0L : toLong(b.get("id")),
                        toLong(a.get("id")) == null ? 0L : toLong(a.get("id"))));
            if (appId != null) {
              sessions.removeIf(
                  s -> !String.valueOf(appId).equals(String.valueOf(s.getOrDefault("appId", "0"))));
            }
            if (StringUtils.isNotBlank(type)) {
              sessions.removeIf(
                  s -> !StringUtils.equalsIgnoreCase(type, String.valueOf(s.get("type"))));
            }
            long cursor = start == null ? 0L : start;
            if (cursor > 0) {
              sessions.removeIf(s -> toLong(s.get("id")) != null && toLong(s.get("id")) >= cursor);
            }
            int pageSize = safePageSize(limit);
            if (sessions.size() > pageSize) {
              return new ArrayList<>(sessions.subList(0, pageSize));
            }
            return sessions;
          }
        });
  }

  @RequestMapping(value = "/reasoner/session/create", method = RequestMethod.POST)
  @ResponseBody
  public HttpResult<Map<String, Object>> createReasonerSession(
      @RequestBody(required = false) Map<String, Object> body) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Map<String, Object>>() {
          @Override
          public void check() {}

          @Override
          public Map<String, Object> action() {
            Map<String, Object> payload = body == null ? new HashMap<>() : body;
            long id = SESSION_ID_ALLOCATOR.incrementAndGet();
            Date now = new Date();
            Map<String, Object> session = new HashMap<>();
            session.put("id", id);
            session.put("name", firstNonBlank(toStr(payload.get("name")), "Session-" + id));
            session.put("description", toNullableStr(payload.get("description")));
            session.put("appId", toLong(payload.get("appId")));
            session.put("type", firstNonBlank(toStr(payload.get("type")), "NORMAL"));
            session.put("gmtCreate", now);
            session.put("gmtModified", now);
            REASONER_SESSION_STORE.put(id, session);
            return session;
          }
        });
  }

  @RequestMapping(value = "/reasoner/session/update", method = RequestMethod.POST)
  @ResponseBody
  public HttpResult<Boolean> updateReasonerSession(
      @RequestBody(required = false) Map<String, Object> body) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Boolean>() {
          @Override
          public void check() {}

          @Override
          public Boolean action() {
            if (body == null) {
              return false;
            }
            Long id = toLong(body.get("id"));
            if (id == null || !REASONER_SESSION_STORE.containsKey(id)) {
              return false;
            }
            Map<String, Object> session = REASONER_SESSION_STORE.get(id);
            if (StringUtils.isNotBlank(toStr(body.get("name")))) {
              session.put("name", toStr(body.get("name")));
            }
            if (body.containsKey("description")) {
              session.put("description", toNullableStr(body.get("description")));
            }
            session.put("gmtModified", new Date());
            return true;
          }
        });
  }

  @RequestMapping(value = "/reasoner/session/delete", method = RequestMethod.POST)
  @ResponseBody
  public HttpResult<Boolean> deleteReasonerSession(
      @RequestBody(required = false) Map<String, Object> body) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Boolean>() {
          @Override
          public void check() {}

          @Override
          public Boolean action() {
            if (body == null) {
              return false;
            }
            Long id = toLong(body.get("id"));
            if (id == null) {
              return false;
            }
            return REASONER_SESSION_STORE.remove(id) != null;
          }
        });
  }

  @RequestMapping(value = "/reasoner/task/mark", method = RequestMethod.POST)
  @ResponseBody
  public HttpResult<Boolean> markReasonerTask(
      @RequestBody(required = false) Map<String, Object> body) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Boolean>() {
          @Override
          public void check() {}

          @Override
          public Boolean action() {
            return body != null;
          }
        });
  }

  @RequestMapping(value = "/reasoner/task/unmark", method = RequestMethod.POST)
  @ResponseBody
  public HttpResult<Boolean> unmarkReasonerTask(
      @RequestBody(required = false) Map<String, Object> body) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Boolean>() {
          @Override
          public void check() {}

          @Override
          public Boolean action() {
            return body != null;
          }
        });
  }

  private List<Map<String, Object>> listStoredReasonerTasks(Long projectId, String keyword) {
    List<Map<String, Object>> store = REASONER_TASK_STORE.get(projectId);
    if (store == null || store.isEmpty()) {
      return new ArrayList<>();
    }
    List<Map<String, Object>> result = new ArrayList<>();
    synchronized (store) {
      for (Map<String, Object> row : store) {
        if (row == null) {
          continue;
        }
        if (StringUtils.isBlank(keyword)) {
          result.add(new HashMap<>(row));
          continue;
        }
        String text = firstNonBlank(toStr(row.get("nl")), toStr(row.get("queryText")));
        if (StringUtils.containsIgnoreCase(firstNonBlank(text, ""), keyword)) {
          result.add(new HashMap<>(row));
        }
      }
    }
    return result;
  }

  private List<Map<String, Object>> paginate(
      List<Map<String, Object>> rows, int pageNo, int pageSize) {
    if (rows == null || rows.isEmpty()) {
      return new ArrayList<>();
    }
    int from = Math.max(0, (pageNo - 1) * pageSize);
    if (from >= rows.size()) {
      return new ArrayList<>();
    }
    int to = Math.min(rows.size(), from + pageSize);
    return new ArrayList<>(rows.subList(from, to));
  }

  private Map<String, Object> toReasonerTaskRowFromRetrieval(
      Long projectId, Integer sessionId, String keyword, String mark, Retrieval retrieval) {
    Date time =
        retrieval.getGmtModified() != null
            ? retrieval.getGmtModified()
            : (retrieval.getGmtCreate() != null ? retrieval.getGmtCreate() : new Date());
    String indexName = firstNonBlank(retrieval.getName(), retrieval.getClassName(), "__ALL__");
    String text =
        firstNonBlank(
            retrieval.getChineseName(), retrieval.getName(), retrieval.getClassName(), "索引召回测试");
    List<String> indexNames = new ArrayList<>();
    indexNames.add(indexName);

    Map<String, Object> row = new HashMap<>();
    row.put("id", retrieval.getId());
    row.put("projectId", projectId);
    row.put("sessionId", sessionId == null ? 0 : sessionId);
    row.put("mark", mark);
    row.put("keyword", keyword);
    row.put("nl", text);
    row.put("query", text);
    row.put("queryText", text);
    row.put("retrievalType", firstNonBlank(retrieval.getType(), "TEXT_SEARCH"));
    row.put("indexType", indexName);
    row.put("startTime", DateTimeUtils.getDate2LongStr(time));
    row.put("params", Collections.singletonMap("config", buildTaskConfig(indexNames, null)));
    row.put("resultMessage", firstNonBlank(retrieval.getConfig(), "{}"));
    row.put("gmtCreate", retrieval.getGmtCreate());
    row.put("gmtModified", retrieval.getGmtModified());
    row.put("status", firstNonBlank(retrieval.getStatus(), "FINISH"));
    row.put("marked", markTask(retrieval.getId(), mark));
    return row;
  }

  private Map<String, Object> toReasonerTaskRowFromBuilder(
      Long projectId, Integer sessionId, String keyword, String mark, BuilderJob job) {
    Date time =
        job.getGmtModified() != null
            ? job.getGmtModified()
            : (job.getGmtCreate() != null ? job.getGmtCreate() : new Date());
    List<String> indexNames = new ArrayList<>();
    indexNames.add("__ALL__");
    String text = firstNonBlank(job.getJobName(), "BuilderTask-" + job.getId());

    Map<String, Object> row = new HashMap<>();
    row.put("id", job.getId());
    row.put("projectId", projectId);
    row.put("sessionId", sessionId == null ? 0 : sessionId);
    row.put("mark", mark);
    row.put("keyword", keyword);
    row.put("nl", text);
    row.put("query", text);
    row.put("queryText", text);
    row.put("retrievalType", firstNonBlank(job.getType(), "BUILDER_JOB"));
    row.put("indexType", "__ALL__");
    row.put("startTime", DateTimeUtils.getDate2LongStr(time));
    row.put("params", Collections.singletonMap("config", buildTaskConfig(indexNames, null)));
    row.put("resultMessage", firstNonBlank(job.getComputingConf(), "{}"));
    row.put("gmtCreate", job.getGmtCreate());
    row.put("gmtModified", job.getGmtModified());
    row.put("status", firstNonBlank(job.getStatus(), "FINISH"));
    row.put("marked", markTask(job.getId(), mark));
    return row;
  }

  private List<Retrieval> resolveProjectRetrievals(Long projectId) {
    List<Retrieval> retrievals = retrievalService.getRetrievalByProjectId(projectId);
    if (retrievals != null && !retrievals.isEmpty()) {
      return retrievals;
    }
    return buildFallbackRetrievals(projectId);
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

  String resolveBuilderFileUrl(Object rawFileUrl) {
    if (rawFileUrl == null) {
      return null;
    }
    if (rawFileUrl instanceof Map) {
      Map<?, ?> map = (Map<?, ?>) rawFileUrl;
      return firstNonBlank(
          toStr(map.get("fileUrl")), toStr(map.get("url")), toStr(map.get("path")));
    }

    String text = toStr(rawFileUrl);
    if (StringUtils.isBlank(text)) {
      return text;
    }
    String trimmed = text.trim();
    if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
      try {
        JSONObject obj = JSON.parseObject(trimmed);
        if (obj != null) {
          return firstNonBlank(
              obj.getString("fileUrl"), obj.getString("url"), obj.getString("path"));
        }
      } catch (Exception ignore) {
        // fallback to parse legacy `key=value` style string
      }

      Matcher fileUrlMatcher = LEGACY_FILE_URL_PATTERN.matcher(trimmed);
      if (fileUrlMatcher.find()) {
        return fileUrlMatcher.group(1).trim();
      }
      Matcher urlMatcher = LEGACY_URL_PATTERN.matcher(trimmed);
      if (urlMatcher.find()) {
        return urlMatcher.group(1).trim();
      }
    }
    return trimmed;
  }

  private String saveLegacyUploadFile(MultipartFile file, String fileName) {
    String sanitizedName =
        Paths.get(firstNonBlank(fileName, "legacy-upload.bin")).getFileName().toString();
    Path targetDir = Paths.get(LEGACY_UPLOAD_ROOT, String.valueOf(System.currentTimeMillis()));
    try {
      Files.createDirectories(targetDir);
      Path target = targetDir.resolve(sanitizedName);
      Files.copy(file.getInputStream(), target, StandardCopyOption.REPLACE_EXISTING);
      return target.toAbsolutePath().toString();
    } catch (IOException ex) {
      throw new RuntimeException("save legacy upload file failed: " + sanitizedName, ex);
    }
  }

  private List<Long> parseLongList(Object value) {
    List<Long> result = new ArrayList<>();
    if (value == null) {
      return result;
    }
    if (value instanceof List) {
      for (Object item : (List<?>) value) {
        Long parsed = toLong(item);
        if (parsed != null) {
          result.add(parsed);
        }
      }
      return result;
    }
    String text = toStr(value);
    if (StringUtils.isBlank(text)) {
      return result;
    }
    text = text.trim();
    if (text.startsWith("[") && text.endsWith("]")) {
      try {
        List<Object> array = JSON.parseArray(text, Object.class);
        for (Object item : array) {
          Long parsed = toLong(item);
          if (parsed != null) {
            result.add(parsed);
          }
        }
        return result;
      } catch (Exception ignore) {
        // ignore and fallback to comma split
      }
    }
    for (String item : text.split(",")) {
      Long parsed = toLong(item);
      if (parsed != null) {
        result.add(parsed);
      }
    }
    return result;
  }

  private List<Retrieval> resolveSelectedRetrievals(
      List<Retrieval> retrievalOptions, List<Long> retrievalIds) {
    List<Retrieval> result = new ArrayList<>();
    if (retrievalOptions == null || retrievalOptions.isEmpty()) {
      return result;
    }
    Map<Long, Retrieval> byId = new HashMap<>();
    for (Retrieval retrieval : retrievalOptions) {
      if (retrieval != null && retrieval.getId() != null) {
        byId.put(retrieval.getId(), retrieval);
      }
    }
    if (retrievalIds != null) {
      for (Long retrievalId : retrievalIds) {
        Retrieval retrieval = byId.get(retrievalId);
        if (retrieval != null) {
          result.add(retrieval);
        }
      }
    }
    if (result.isEmpty()) {
      result.add(retrievalOptions.get(0));
    }
    return result;
  }

  private Set<String> resolveLabelConstraints(List<Retrieval> selectedRetrievals) {
    Set<String> labels = new LinkedHashSet<>();
    if (selectedRetrievals == null || selectedRetrievals.isEmpty()) {
      return labels;
    }
    for (Retrieval retrieval : selectedRetrievals) {
      if (retrieval == null) {
        continue;
      }
      String label = firstNonBlank(retrieval.getClassName(), retrieval.getName());
      if (StringUtils.isBlank(label)) {
        continue;
      }
      for (String item : label.split(",")) {
        String normalized = item == null ? "" : item.trim();
        if (StringUtils.isBlank(normalized)
            || StringUtils.equalsIgnoreCase(normalized, "all")
            || StringUtils.equalsIgnoreCase(normalized, "__ALL__")) {
          continue;
        }
        labels.add(normalized);
      }
    }
    return labels;
  }

  private List<IdxRecord> searchTextRecords(
      Long projectId, String query, Set<String> labels, int topk, boolean fallbackToAll) {
    if (projectId == null) {
      return new ArrayList<>();
    }
    TextSearchRequest request = new TextSearchRequest();
    request.setProjectId(projectId);
    String normalizedQuery = StringUtils.isBlank(query) ? "*" : query.trim();
    request.setQueryString(normalizedQuery);
    request.setPage(1);
    request.setTopk(Math.max(topk, 1));
    if (labels != null && !labels.isEmpty()) {
      request.setLabelConstraints(labels);
    }
    try {
      List<IdxRecord> records = searchManager.textSearch(request);
      if ((records == null || records.isEmpty())
          && fallbackToAll
          && labels != null
          && !labels.isEmpty()) {
        request.setLabelConstraints(null);
        records = searchManager.textSearch(request);
      }
      if ((records == null || records.isEmpty())
          && fallbackToAll
          && !StringUtils.equals(normalizedQuery, "*")) {
        String looseQuery = buildLooseQuery(normalizedQuery);
        if (StringUtils.isNotBlank(looseQuery)
            && !StringUtils.equals(looseQuery, normalizedQuery)) {
          request.setLabelConstraints(null);
          request.setQueryString(looseQuery);
          records = searchManager.textSearch(request);
        }
      }
      if ((records == null || records.isEmpty())
          && fallbackToAll
          && !StringUtils.equals(normalizedQuery, "*")) {
        request.setLabelConstraints(null);
        request.setQueryString("*");
        records = searchManager.textSearch(request);
      }
      return records == null ? new ArrayList<>() : records;
    } catch (Exception ex) {
      log.warn("search text records failed, projectId={}, query={}", projectId, query, ex);
      return new ArrayList<>();
    }
  }

  private String buildLooseQuery(String query) {
    if (StringUtils.isBlank(query)) {
      return "*";
    }
    String normalized = query.trim();
    if (StringUtils.equals(normalized, "*")) {
      return "*";
    }
    String[] tokens = normalized.split("[\\s,，。;；|/]+");
    String best = "";
    for (String token : tokens) {
      if (StringUtils.isBlank(token)) {
        continue;
      }
      String candidate = token.trim();
      if (candidate.length() > best.length()) {
        best = candidate;
      }
    }
    if (StringUtils.isBlank(best)) {
      best = normalized;
    }
    if (best.length() > 6) {
      return best.substring(0, 6);
    }
    return best;
  }

  private List<Map<String, Object>> buildReferenceInfo(List<IdxRecord> records) {
    List<Map<String, Object>> result = new ArrayList<>();
    if (records == null || records.isEmpty()) {
      return result;
    }
    int index = 0;
    for (IdxRecord record : records) {
      if (record == null) {
        continue;
      }
      Map<String, Object> fields =
          record.getFields() == null ? Collections.emptyMap() : record.getFields();
      String docId = firstNonBlank(record.getDocId(), "doc-" + index);
      String title = firstNonBlank(toStr(fields.get("title")), toStr(fields.get("name")), docId);
      String content =
          firstNonBlank(
              toStr(fields.get("content")),
              toStr(fields.get("description")),
              toStr(fields.get("summary")),
              title);
      content = StringUtils.isBlank(content) ? docId : content.trim();
      if (content.length() > 1000) {
        content = content.substring(0, 1000);
      }

      Map<String, Object> row = new HashMap<>();
      row.put("id", docId + "_" + index);
      row.put("docId", docId);
      row.put("title", title);
      row.put("content", content);
      row.put("label", record.getLabel());
      row.put("score", record.getScore());
      result.add(row);
      index++;
    }
    return result;
  }

  private List<String> buildCallbackSegmentation(List<Map<String, Object>> referenceInfo) {
    List<String> result = new ArrayList<>();
    if (referenceInfo == null || referenceInfo.isEmpty()) {
      return result;
    }
    for (Map<String, Object> item : referenceInfo) {
      String content = toStr(item.get("content"));
      if (StringUtils.isBlank(content)) {
        continue;
      }
      String normalized = content.replace("\r\n", "\n").replace("\r", "\n").trim();
      if (normalized.length() > 240) {
        normalized = normalized.substring(0, 240);
      }
      result.add(normalized);
      if (result.size() >= 8) {
        break;
      }
    }
    return result;
  }

  private List<Map<String, Object>> buildSubgraphs(
      List<IdxRecord> records, List<Retrieval> selectedRetrievals) {
    List<Map<String, Object>> result = new ArrayList<>();
    if (records == null || records.isEmpty()) {
      return result;
    }

    List<Map<String, Object>> nodes = new ArrayList<>();
    List<Map<String, Object>> edges = new ArrayList<>();
    String firstNodeId = null;
    int index = 0;
    for (IdxRecord record : records) {
      if (record == null) {
        continue;
      }
      Map<String, Object> fields =
          record.getFields() == null ? Collections.emptyMap() : record.getFields();
      String docId = firstNonBlank(record.getDocId(), "node-" + index);
      String nodeId = docId + "_" + index;
      String label = firstNonBlank(record.getLabel(), "Chunk");
      String name = firstNonBlank(toStr(fields.get("name")), toStr(fields.get("title")), docId);
      String content =
          firstNonBlank(
              toStr(fields.get("content")),
              toStr(fields.get("description")),
              toStr(fields.get("summary")),
              name);

      Map<String, Object> properties = new HashMap<>();
      properties.put("id", docId);
      properties.put("name", name);
      properties.put("content", content);
      properties.put("score", record.getScore());

      Map<String, Object> node = new HashMap<>();
      node.put("id", nodeId);
      node.put("label", label);
      node.put("properties", properties);
      nodes.add(node);

      if (firstNodeId == null) {
        firstNodeId = nodeId;
      } else {
        Map<String, Object> edge = new HashMap<>();
        edge.put("id", "edge_" + index);
        edge.put("from", firstNodeId);
        edge.put("to", nodeId);
        edge.put("label", "related");
        edge.put("properties", Collections.singletonMap("name", "related"));
        edges.add(edge);
      }
      index++;
    }

    Map<String, Object> subgraph = new HashMap<>();
    String className = "legacy-search";
    if (selectedRetrievals != null && !selectedRetrievals.isEmpty()) {
      Retrieval retrieval = selectedRetrievals.get(0);
      className = firstNonBlank(retrieval.getName(), retrieval.getClassName(), className);
    }
    subgraph.put("className", className);
    subgraph.put("resultNodes", nodes);
    subgraph.put("resultEdges", edges);
    result.add(subgraph);
    return result;
  }

  private String buildTaskConfig(List<String> indexNames, Map<String, Object> request) {
    JSONObject config = new JSONObject();
    JSONObject chat = new JSONObject();
    chat.put("index_list", indexNames == null ? new ArrayList<>() : indexNames);
    if (request != null) {
      String solverHttpAddr = toNullableStr(request.get("solverHttpAddr"));
      String kagHostAddr = toNullableStr(request.get("kagHostAddr"));
      if (StringUtils.isNotBlank(solverHttpAddr)) {
        chat.put("maya_http", solverHttpAddr);
      }
      if (StringUtils.isNotBlank(kagHostAddr)) {
        chat.put("host_addr", kagHostAddr);
      }
    }
    config.put("chat", chat);

    if (request != null && request.get("llm") != null) {
      Object llm = request.get("llm");
      if (llm instanceof String && StringUtils.isNotBlank((String) llm)) {
        try {
          config.put("llm", JSON.parseObject((String) llm));
        } catch (Exception ex) {
          config.put("llm", llm);
        }
      } else {
        config.put("llm", llm);
      }
    }
    return config.toJSONString();
  }

  private void saveReasonerTask(
      long taskId,
      Long projectId,
      Long sessionId,
      String instruction,
      List<Retrieval> selectedRetrievals,
      String resultMessage,
      Map<String, Object> request) {
    if (projectId == null) {
      return;
    }
    Date now = new Date();
    List<String> indexNames = new ArrayList<>();
    if (selectedRetrievals != null) {
      for (Retrieval retrieval : selectedRetrievals) {
        if (retrieval == null) {
          continue;
        }
        String name = firstNonBlank(retrieval.getName(), retrieval.getClassName());
        if (StringUtils.isNotBlank(name)) {
          indexNames.add(name);
        }
      }
    }

    Map<String, Object> row = new HashMap<>();
    row.put("id", taskId);
    row.put("projectId", projectId);
    row.put("sessionId", sessionId == null ? 0 : sessionId);
    row.put("mark", null);
    row.put("keyword", instruction);
    row.put("nl", instruction);
    row.put("query", instruction);
    row.put("queryText", instruction);
    row.put("retrievalType", "TEXT_SEARCH");
    row.put("indexType", indexNames.isEmpty() ? "__ALL__" : String.join(",", indexNames));
    row.put("startTime", DateTimeUtils.getDate2LongStr(now));
    row.put("params", Collections.singletonMap("config", buildTaskConfig(indexNames, request)));
    row.put("resultMessage", resultMessage);
    row.put("gmtCreate", now);
    row.put("gmtModified", now);
    row.put("status", "FINISH");
    row.put("marked", false);

    List<Map<String, Object>> store =
        REASONER_TASK_STORE.computeIfAbsent(projectId, k -> new ArrayList<>());
    synchronized (store) {
      store.add(0, row);
      if (store.size() > 200) {
        store.subList(200, store.size()).clear();
      }
    }
  }

  private Map<String, Object> defaultBuilderQueryResult() {
    Map<String, Object> result = new HashMap<>();
    result.put("resultNodes", new ArrayList<>());
    result.put("resultEdges", new ArrayList<>());
    result.put("resultMessage", "[]");
    return result;
  }

  private void fillBuilderQueryResult(Map<String, Object> result, Retrieval retrieval) {
    if (retrieval == null) {
      return;
    }
    result.put("id", retrieval.getId());
    result.put("name", retrieval.getName());
    result.put("className", retrieval.getClassName());
    result.put("status", retrieval.getStatus());
    result.put("gmtCreate", retrieval.getGmtCreate());
    result.put("gmtModified", retrieval.getGmtModified());
    result.put("resultMessage", firstNonBlank(retrieval.getConfig(), "[]"));
  }

  private void fillBuilderQuerySampleResult(
      Map<String, Object> result, Long projectId, Retrieval retrieval, BuilderJob builderJob) {
    if (projectId == null || result == null) {
      return;
    }
    List<Retrieval> selectedRetrievals = new ArrayList<>();
    if (retrieval != null) {
      selectedRetrievals.add(retrieval);
    }
    Set<String> labelConstraints = resolveLabelConstraints(selectedRetrievals);
    String query = resolveBuilderSampleQuery(builderJob, retrieval);
    List<IdxRecord> records = searchTextRecords(projectId, query, labelConstraints, 8, true);
    if ((records == null || records.isEmpty()) && builderJob != null) {
      records = buildSampleRecordsFromBuilderJob(builderJob, 8);
    }
    if (records == null || records.isEmpty()) {
      return;
    }
    List<Map<String, Object>> subgraphs = buildSubgraphs(records, selectedRetrievals);
    if (subgraphs == null || subgraphs.isEmpty()) {
      return;
    }
    Map<String, Object> subgraph = subgraphs.get(0);
    Object nodes = subgraph.get("resultNodes");
    Object edges = subgraph.get("resultEdges");
    result.put("resultNodes", nodes instanceof List ? nodes : new ArrayList<>());
    result.put("resultEdges", edges instanceof List ? edges : new ArrayList<>());
  }

  private String resolveBuilderSampleQuery(BuilderJob builderJob, Retrieval retrieval) {
    String query =
        builderJob == null
            ? null
            : firstNonBlank(builderJob.getJobName(), builderJob.getFileUrl(), builderJob.getType());
    if (StringUtils.isBlank(query) && retrieval != null) {
      query =
          firstNonBlank(retrieval.getChineseName(), retrieval.getName(), retrieval.getClassName());
    }
    return firstNonBlank(query, "*");
  }

  private List<IdxRecord> buildSampleRecordsFromBuilderJob(BuilderJob builderJob, int topk) {
    List<IdxRecord> result = new ArrayList<>();
    if (builderJob == null) {
      return result;
    }
    try {
      if (StringUtils.isNotBlank(builderJob.getComputingConf())) {
        JSONObject conf = JSON.parseObject(builderJob.getComputingConf());
        if (conf != null) {
          JSONObject envs = conf.getJSONObject("envs");
          if (envs != null) {
            String payload = toStr(envs.get("OPENSPG_DEMO_BATCH_GZIP_B64"));
            if (StringUtils.isNotBlank(payload)) {
              byte[] compressed = Base64.getDecoder().decode(payload);
              String jsonl = gunzipToString(compressed);
              if (StringUtils.isNotBlank(jsonl)) {
                int index = 0;
                for (String line : jsonl.split("\n")) {
                  if (index >= Math.max(topk, 1)) {
                    break;
                  }
                  if (StringUtils.isBlank(line)) {
                    continue;
                  }
                  JSONObject item;
                  try {
                    item = JSON.parseObject(line.trim());
                  } catch (Exception parseEx) {
                    continue;
                  }
                  String docId =
                      firstNonBlank(
                          toStr(item.get("doc_id")), toStr(item.get("id")), "doc-" + index);
                  String title =
                      firstNonBlank(toStr(item.get("title")), toStr(item.get("name")), docId);
                  String content =
                      firstNonBlank(
                          toStr(item.get("summary")),
                          toStr(item.get("content")),
                          toStr(item.get("description")),
                          title);
                  Map<String, Object> fields = new HashMap<>();
                  fields.put("title", title);
                  fields.put("name", title);
                  fields.put("content", content);
                  fields.put("source", toStr(item.get("source_name")));
                  fields.put("url", toStr(item.get("source_url")));
                  double score = Math.max(0.1d, 1.0d - index * 0.05d);
                  IdxRecord record = new IdxRecord("openspg_demo_batch", docId, score, fields);
                  record.setLabel(
                      firstNonBlank(
                          toStr(item.get("record_type")), toStr(item.get("type")), "Document"));
                  result.add(record);
                  index++;
                }
              }
            }
          }
        }
      }
    } catch (Exception ex) {
      log.warn("build sample records from builder job failed, jobId={}", builderJob.getId(), ex);
    }
    if (!result.isEmpty()) {
      return result;
    }
    return buildSampleRecordsFromBuilderFile(builderJob, topk);
  }

  private List<IdxRecord> buildSampleRecordsFromBuilderFile(BuilderJob builderJob, int topk) {
    List<IdxRecord> result = new ArrayList<>();
    String fileUrl = resolveBuilderFileUrl(builderJob.getFileUrl());
    if (StringUtils.isBlank(fileUrl)) {
      return result;
    }
    try {
      Path path = Paths.get(fileUrl);
      if (!Files.exists(path) || !Files.isRegularFile(path)) {
        return result;
      }
      String raw = new String(Files.readAllBytes(path), StandardCharsets.UTF_8);
      String text = StringUtils.isBlank(raw) ? "" : raw.replace("\r\n", "\n").replace("\r", "\n");
      if (StringUtils.isBlank(text)) {
        return result;
      }

      List<IdxRecord> companies =
          buildCompanySampleRecords(text, path.getFileName().toString(), topk);
      if (!companies.isEmpty()) {
        return companies;
      }

      int limit = Math.max(topk, 1);
      int index = 0;
      for (String block : text.split("\\n\\s*\\n")) {
        if (index >= limit) {
          break;
        }
        if (StringUtils.isBlank(block)) {
          continue;
        }
        String content = block.trim().replaceAll("(?m)^#+\\s*", "");
        if (StringUtils.isBlank(content)) {
          continue;
        }
        if (content.length() > 600) {
          content = content.substring(0, 600);
        }
        String docId = "legacy-file-" + index;
        Map<String, Object> fields = new HashMap<>();
        fields.put("title", path.getFileName().toString() + "-chunk-" + (index + 1));
        fields.put("name", fields.get("title"));
        fields.put("content", content);
        double score = Math.max(0.1d, 1.0d - index * 0.05d);
        IdxRecord record = new IdxRecord("legacy_builder_file", docId, score, fields);
        record.setLabel("Document");
        result.add(record);
        index++;
      }
      return result;
    } catch (Exception ex) {
      log.warn(
          "build sample records from builder file failed, jobId={}, fileUrl={}",
          builderJob.getId(),
          fileUrl,
          ex);
      return result;
    }
  }

  private List<IdxRecord> buildCompanySampleRecords(String text, String sourceName, int topk) {
    List<IdxRecord> result = new ArrayList<>();
    Matcher matcher = COMPANY_CANDIDATE_PATTERN.matcher(text);
    Set<String> names = new LinkedHashSet<>();
    while (matcher.find() && names.size() < Math.max(topk, 1)) {
      String candidate = matcher.group(1);
      if (StringUtils.isBlank(candidate)) {
        continue;
      }
      String name = candidate.trim();
      if (name.length() < 2 || name.length() > 80) {
        continue;
      }
      names.add(name);
    }
    int index = 0;
    for (String name : names) {
      String content = extractSnippet(text, name, 80);
      Map<String, Object> fields = new HashMap<>();
      fields.put("title", name);
      fields.put("name", name);
      fields.put("content", content);
      fields.put("source", sourceName);
      double score = Math.max(0.1d, 1.0d - index * 0.05d);
      IdxRecord record = new IdxRecord("legacy_builder_company", "company-" + index, score, fields);
      record.setLabel("Company");
      result.add(record);
      index++;
      if (index >= Math.max(topk, 1)) {
        break;
      }
    }
    return result;
  }

  private String extractSnippet(String text, String keyword, int window) {
    if (StringUtils.isBlank(text) || StringUtils.isBlank(keyword)) {
      return firstNonBlank(keyword, "");
    }
    int idx = text.indexOf(keyword);
    if (idx < 0) {
      return keyword;
    }
    int left = Math.max(0, idx - Math.max(window, 20));
    int right = Math.min(text.length(), idx + keyword.length() + Math.max(window, 20));
    return text.substring(left, right).replace("\n", " ").trim();
  }

  private String gunzipToString(byte[] compressed) {
    if (compressed == null || compressed.length == 0) {
      return "";
    }
    try (ByteArrayInputStream in = new ByteArrayInputStream(compressed);
        GZIPInputStream gzipIn = new GZIPInputStream(in);
        ByteArrayOutputStream out = new ByteArrayOutputStream()) {
      byte[] buffer = new byte[4096];
      int n;
      while ((n = gzipIn.read(buffer)) > 0) {
        out.write(buffer, 0, n);
      }
      return new String(out.toByteArray(), StandardCharsets.UTF_8);
    } catch (Exception ex) {
      return "";
    }
  }

  private boolean markTask(Long taskId, String mark) {
    if (taskId == null) {
      return false;
    }
    if (StringUtils.equalsIgnoreCase(mark, "MARKED")) {
      return true;
    }
    return false;
  }

  private SchedulerJob createSchedulerJob(BuilderJob taskJob) {
    SchedulerJob job = new SchedulerJob();
    job.setProjectId(taskJob.getProjectId());
    job.setName(taskJob.getJobName());
    job.setCreateUser(taskJob.getCreateUser());
    job.setModifyUser(taskJob.getModifyUser());
    job.setLifeCycle(parseLifeCycle(taskJob.getLifeCycle()));
    job.setStatus(SchedulerEnum.Status.ENABLE);
    job.setTranslateType(resolveTranslateType(taskJob.getType()));
    job.setDependence(parseDependence(taskJob.getDependence()));
    job.setInvokerId(taskJob.getId().toString());
    return schedulerService.submitJob(job);
  }

  private SchedulerEnum.LifeCycle parseLifeCycle(String lifeCycle) {
    if (StringUtils.isBlank(lifeCycle)) {
      return SchedulerEnum.LifeCycle.ONCE;
    }
    try {
      return SchedulerEnum.LifeCycle.valueOf(lifeCycle.toUpperCase());
    } catch (Exception ex) {
      return SchedulerEnum.LifeCycle.ONCE;
    }
  }

  private SchedulerEnum.Dependence parseDependence(String dependence) {
    if (StringUtils.isBlank(dependence)) {
      return SchedulerEnum.Dependence.INDEPENDENT;
    }
    try {
      return SchedulerEnum.Dependence.valueOf(dependence.toUpperCase());
    } catch (Exception ex) {
      return SchedulerEnum.Dependence.INDEPENDENT;
    }
  }

  private SchedulerEnum.TranslateType resolveTranslateType(String type) {
    String normalized = StringUtils.isBlank(type) ? "" : type.toLowerCase();
    if (normalized.contains("command")) {
      return SchedulerEnum.TranslateType.KAG_COMMAND_BUILDER;
    }
    if (normalized.contains("structure")) {
      return SchedulerEnum.TranslateType.KAG_STRUCTURE_BUILDER;
    }
    if (normalized.contains("entire")) {
      return SchedulerEnum.TranslateType.KAG_ENTIRETY_BUILDER;
    }
    return SchedulerEnum.TranslateType.KAG_BUILDER;
  }

  private String resolveComputingConf(Map<String, Object> body) {
    Object computingConf = body.get("computingConf");
    if (computingConf instanceof String && StringUtils.isNotBlank((String) computingConf)) {
      return (String) computingConf;
    }
    if (computingConf instanceof Map) {
      return JSON.toJSONString(computingConf);
    }

    JSONObject conf = new JSONObject();
    conf.put("command", firstNonBlank(toStr(body.get("command")), "echo legacy builder job"));
    conf.put("workerNum", toInt(body.get("workerNum"), 1));
    if (body.get("envs") instanceof Map) {
      conf.put("envs", body.get("envs"));
    }
    return conf.toJSONString();
  }

  private Long normalizeProjectId(Long projectId) {
    if (projectId != null && projectManager.queryById(projectId) != null) {
      return projectId;
    }
    ProjectQueryRequest request = new ProjectQueryRequest();
    List<Project> projects = projectManager.queryPageData(request, 0, 1);
    if (projects == null || projects.isEmpty()) {
      return projectId == null ? 1L : projectId;
    }
    return projects.get(0).getId();
  }

  private String getCurrentUserNo() {
    try {
      Account account = getLoginAccount();
      if (account != null && StringUtils.isNotBlank(account.getWorkNo())) {
        return account.getWorkNo();
      }
    } catch (Exception ignore) {
      // ignore
    }
    return "openspg";
  }

  private String firstNonBlank(String... values) {
    if (values == null || values.length == 0) {
      return null;
    }
    for (String value : values) {
      if (StringUtils.isNotBlank(value)) {
        return value;
      }
    }
    return null;
  }

  private String toStr(Object value) {
    return value == null ? null : String.valueOf(value);
  }

  private String toNullableStr(Object value) {
    String v = toStr(value);
    return StringUtils.isBlank(v) ? null : v;
  }

  private Long toLong(Object value) {
    if (value instanceof Long) {
      return (Long) value;
    }
    if (value instanceof Integer) {
      return ((Integer) value).longValue();
    }
    if (value == null) {
      return null;
    }
    try {
      return Long.parseLong(String.valueOf(value));
    } catch (Exception ex) {
      return null;
    }
  }

  private Integer toInt(Object value, int defaultVal) {
    if (value instanceof Integer) {
      return (Integer) value;
    }
    if (value instanceof Long) {
      long longVal = (Long) value;
      if (longVal > Integer.MAX_VALUE) {
        return Integer.MAX_VALUE;
      }
      if (longVal < Integer.MIN_VALUE) {
        return Integer.MIN_VALUE;
      }
      return (int) longVal;
    }
    if (value == null) {
      return defaultVal;
    }
    try {
      return Integer.parseInt(String.valueOf(value));
    } catch (Exception ex) {
      return defaultVal;
    }
  }

  private int safePageNo(Long start) {
    if (start == null || start < 1) {
      return 1;
    }
    if (start > Integer.MAX_VALUE) {
      return Integer.MAX_VALUE;
    }
    return start.intValue();
  }

  private int safePageSize(Integer limit) {
    if (limit == null || limit < 1) {
      return 10;
    }
    return Math.min(limit, 1000);
  }
}
