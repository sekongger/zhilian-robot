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
import com.antgroup.openspg.common.util.enums.PermissionEnum;
import com.antgroup.openspg.common.util.enums.ResourceTagEnum;
import com.antgroup.openspg.server.api.facade.dto.common.request.ProjectQueryRequest;
import com.antgroup.openspg.server.api.facade.dto.service.request.TextSearchRequest;
import com.antgroup.openspg.server.api.http.server.BaseController;
import com.antgroup.openspg.server.api.http.server.HttpBizCallback;
import com.antgroup.openspg.server.api.http.server.HttpBizTemplate;
import com.antgroup.openspg.server.api.http.server.HttpResult;
import com.antgroup.openspg.server.biz.common.AccountManager;
import com.antgroup.openspg.server.biz.common.ConfigManager;
import com.antgroup.openspg.server.biz.common.PermissionManager;
import com.antgroup.openspg.server.biz.common.ProjectManager;
import com.antgroup.openspg.server.biz.service.SearchManager;
import com.antgroup.openspg.server.common.model.account.Account;
import com.antgroup.openspg.server.common.model.config.Config;
import com.antgroup.openspg.server.common.model.permission.Permission;
import com.antgroup.openspg.server.common.model.project.Project;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseBody;

/**
 * Legacy UI compatibility endpoints for the built-in front-end.
 *
 * <p>The bundled UI still uses `/v1/**` routes. The open-source server primarily exposes
 * `/public/v1/**`, which causes 404 in local demo mode. This controller keeps the old UI routes
 * available so pages like `#/knowledge` can load project/account/permission/config data.
 */
@Controller
@RequestMapping("/v1")
@Slf4j
public class LegacyUiCompatController extends BaseController {

  private static final String DEFAULT_USER_NO = "openspg";

  @Autowired private ProjectManager projectManager;
  @Autowired private ConfigManager configManager;
  @Autowired private AccountManager accountManager;
  @Autowired private PermissionManager permissionManager;
  @Autowired private SearchManager searchManager;

  @RequestMapping(value = "/projects/list", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<Map<String, Object>> getProjectList(
      @RequestParam(required = false) Boolean isOwner,
      @RequestParam(required = false) String queryStr,
      @RequestParam(required = false) Integer pageNo,
      @RequestParam(required = false) Integer pageSize) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Map<String, Object>>() {
          @Override
          public void check() {}

          @Override
          public Map<String, Object> action() {
            int safePageNo = pageNo == null || pageNo < 1 ? 1 : pageNo;
            int safePageSize = pageSize == null || pageSize < 1 ? 20 : Math.min(pageSize, 1000);

            ProjectQueryRequest request = new ProjectQueryRequest();
            request.setOwner(isOwner);
            if (StringUtils.isNotBlank(queryStr)) {
              request.setName(queryStr);
            }

            Long totalCount = projectManager.queryPageCount(request);
            List<Project> projects =
                projectManager.queryPageData(
                    request, (safePageNo - 1) * safePageSize, safePageSize);

            List<Map<String, Object>> data = new ArrayList<>();
            if (projects != null) {
              for (Project project : projects) {
                data.add(toLegacyProject(project));
              }
            }

            Map<String, Object> result = new HashMap<>();
            result.put("data", data);
            result.put("total", totalCount == null ? 0L : totalCount);
            result.put("pageNo", safePageNo);
            result.put("pageSize", safePageSize);
            return result;
          }
        });
  }

  @RequestMapping(value = "/projects/{projectId}", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<Map<String, Object>> getProjectInfo(@PathVariable("projectId") Long projectId) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Map<String, Object>>() {
          @Override
          public void check() {}

          @Override
          public Map<String, Object> action() {
            Project project = projectManager.queryById(projectId);
            if (project == null) {
              return null;
            }
            return toLegacyProject(project);
          }
        });
  }

  @RequestMapping(value = "/configs/{configId}/version/{version}", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<Config> getConfig(
      @PathVariable("configId") String configId, @PathVariable("version") String version) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Config>() {
          @Override
          public void check() {}

          @Override
          public Config action() {
            Config config = configManager.query(configId, version);
            if (config == null && StringUtils.isNotBlank(configId) && !"1".equals(version)) {
              return configManager.query(configId, "1");
            }
            return config;
          }
        });
  }

  @RequestMapping(
      value = {"/accounts", "/accounts/"},
      method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<Account> getAccount() {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Account>() {
          @Override
          public void check() {}

          @Override
          public Account action() {
            Account account = accountManager.getByUserNo(DEFAULT_USER_NO);
            if (account == null) {
              account = new Account();
              account.setWorkNo(DEFAULT_USER_NO);
              account.setAccount(DEFAULT_USER_NO);
              account.setRealName(DEFAULT_USER_NO);
              account.setNickName(DEFAULT_USER_NO);
              account.setUseCurrentLanguage("zh-CN");
            }
            if (account.getRoleNames() == null || account.getRoleNames().isEmpty()) {
              account.setRoleNames(Collections.singletonList(PermissionEnum.SUPER.name()));
            }
            return account;
          }
        });
  }

  @RequestMapping(value = "/accounts/updateUserConfig", method = RequestMethod.POST)
  @ResponseBody
  public HttpResult<Integer> updateUserConfig(
      @RequestBody(required = false) Map<String, Object> body) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Integer>() {
          @Override
          public void check() {}

          @Override
          public Integer action() {
            if (body == null || body.get("config") == null) {
              return 0;
            }
            String config = String.valueOf(body.get("config"));
            if (StringUtils.isBlank(config)) {
              return 0;
            }
            return accountManager.updateUserConfig(DEFAULT_USER_NO, config);
          }
        });
  }

  @RequestMapping(value = "/permissions/getPermissionList", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<Map<String, Object>> getPermissionList() {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Map<String, Object>>() {
          @Override
          public void check() {}

          @Override
          public Map<String, Object> action() {
            List<Permission> permissionList = new ArrayList<>();
            appendPermission(permissionList, ResourceTagEnum.PLATFORM.name());
            appendPermission(permissionList, ResourceTagEnum.APP.name());
            appendPermission(permissionList, ResourceTagEnum.KNOWLEDGE_BASE.name());

            Map<String, Object> result = new HashMap<>();
            result.put("permissionList", permissionList);
            return result;
          }
        });
  }

  @RequestMapping(value = "/permissions/{resourceTag}/id/{resourceId}", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<Map<String, Object>> getPermissionPage(
      @PathVariable("resourceTag") String resourceTag,
      @PathVariable("resourceId") Long resourceId,
      @RequestParam(required = false) String queryStr,
      @RequestParam(required = false) String roleType,
      @RequestParam(required = false) Integer pageNo,
      @RequestParam(required = false) Integer pageSize) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Map<String, Object>>() {
          @Override
          public void check() {}

          @Override
          public Map<String, Object> action() {
            int safePageNo = pageNo == null || pageNo < 1 ? 1 : pageNo;
            int safePageSize = pageSize == null || pageSize < 1 ? 10 : Math.min(pageSize, 1000);
            long offset = (long) (safePageNo - 1) * safePageSize;

            List<Permission> permissions =
                permissionManager.selectLikeByUserNoAndRoleId(
                    queryStr, roleType, resourceId, resourceTag, offset, (long) safePageSize);
            long total =
                permissionManager.selectLikeCountByUserNoAndRoleId(
                    queryStr, roleType, resourceId, resourceTag);

            List<Map<String, Object>> data = new ArrayList<>();
            if (permissions != null) {
              for (Permission permission : permissions) {
                Map<String, Object> row = new HashMap<>();
                row.put("id", permission.getId());
                row.put("userNo", permission.getUserNo());
                row.put("resourceId", permission.getResourceId());
                row.put("resourceTag", permission.getResourceTag());
                row.put("roleId", permission.getRoleId());
                row.put("roleType", permission.getRoleType());
                row.put("userName", permission.getUserName());

                Account account = accountManager.getByUserNo(permission.getUserNo());
                if (account != null) {
                  row.put("account", account.getAccount());
                  row.put("realName", account.getRealName());
                  row.put("nickName", account.getNickName());
                }
                data.add(row);
              }
            }

            Map<String, Object> result = new HashMap<>();
            result.put("data", data);
            result.put("results", data);
            result.put("total", total);
            result.put("pageNo", safePageNo);
            result.put("pageSize", safePageSize);
            return result;
          }
        });
  }

  @RequestMapping(value = "/datas/getEnumValues/{enumName}", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<List<Map<String, Object>>> getEnumValuesByPath(
      @PathVariable("enumName") String enumName, @RequestParam(required = false) String name) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<List<Map<String, Object>>>() {
          @Override
          public void check() {}

          @Override
          public List<Map<String, Object>> action() {
            return buildEnumValues(StringUtils.isBlank(name) ? enumName : name);
          }
        });
  }

  @RequestMapping(value = "/datas/getEnumValues", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<List<Map<String, Object>>> getEnumValues(
      @RequestParam(required = false) String name) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<List<Map<String, Object>>>() {
          @Override
          public void check() {}

          @Override
          public List<Map<String, Object>> action() {
            return buildEnumValues(name);
          }
        });
  }

  @RequestMapping(value = "/datas/search", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<Map<String, Object>> searchData(
      @RequestParam Long projectId,
      @RequestParam(required = false) String queryStr,
      @RequestParam(required = false) String label,
      @RequestParam(required = false) Integer page,
      @RequestParam(required = false) Integer size,
      @RequestParam(required = false) Boolean matchExactOnly) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Map<String, Object>>() {
          @Override
          public void check() {}

          @Override
          public Map<String, Object> action() {
            int safePage = page == null || page < 1 ? 1 : page;
            int safeSize = size == null || size < 1 ? 20 : Math.min(size, 200);
            String safeQuery = StringUtils.isBlank(queryStr) ? "*" : queryStr.trim();

            TextSearchRequest request = new TextSearchRequest();
            request.setProjectId(projectId);
            request.setQueryString(safeQuery);
            request.setPage(safePage);
            request.setTopk(safeSize);
            Set<String> labelConstraints = parseLabelConstraints(label);
            if (!labelConstraints.isEmpty()) {
              request.setLabelConstraints(labelConstraints);
            }

            List<IdxRecord> records = searchManager.textSearch(request);
            List<Map<String, Object>> data = new ArrayList<>();
            if (records != null) {
              for (IdxRecord record : records) {
                Map<String, Object> fields =
                    record.getFields() == null ? Collections.emptyMap() : record.getFields();
                String name = valueAsString(fields.get("name"));
                if (StringUtils.isBlank(name)) {
                  name = valueAsString(fields.get("title"));
                }
                if (StringUtils.isBlank(name)) {
                  name = record.getDocId();
                }

                if (Boolean.TRUE.equals(matchExactOnly) && StringUtils.isNotBlank(queryStr)) {
                  if (!StringUtils.equals(name, queryStr.trim())) {
                    continue;
                  }
                }

                Map<String, Object> row = new HashMap<>();
                row.put("id", record.getDocId());
                row.put("docId", record.getDocId());
                row.put("name", name);
                row.put("queryText", name);
                row.put("label", record.getLabel());
                row.put("type", record.getLabel());
                row.put("idxName", record.getIdxName());
                row.put("score", record.getScore());
                row.put("fields", fields);
                data.add(row);
              }
            }

            Map<String, Object> result = new HashMap<>();
            result.put("data", data);
            result.put("results", data);
            result.put("total", (long) data.size());
            result.put("pageNo", safePage);
            result.put("pageSize", safeSize);
            result.put("queryStr", safeQuery);
            result.put("label", label);
            return result;
          }
        });
  }

  private Set<String> parseLabelConstraints(String label) {
    if (StringUtils.isBlank(label)) {
      return Collections.emptySet();
    }
    String text = label.trim();
    if ("all".equalsIgnoreCase(text) || "*".equals(text)) {
      return Collections.emptySet();
    }
    Set<String> labels = new HashSet<>();
    for (String item : text.split(",")) {
      if (StringUtils.isBlank(item)) {
        continue;
      }
      labels.add(item.trim());
    }
    return labels;
  }

  private String valueAsString(Object value) {
    return value == null ? "" : String.valueOf(value);
  }

  private List<Map<String, Object>> buildEnumValues(String enumName) {
    if (StringUtils.isBlank(enumName)) {
      return Collections.emptyList();
    }
    if (!"BuilderJobStatus".equalsIgnoreCase(enumName)) {
      return Collections.emptyList();
    }
    List<Map<String, Object>> result = new ArrayList<>();
    for (String status : Arrays.asList("CREATED", "RUNNING", "FINISH", "FAIL")) {
      Map<String, Object> item = new HashMap<>();
      item.put("name", status);
      item.put("label", status);
      item.put("text", status);
      item.put("key", status);
      item.put("value", status);
      result.add(item);
    }
    return result;
  }

  private void appendPermission(List<Permission> target, String resourceTag) {
    List<Permission> permissions =
        permissionManager.getPermissionByUserNoAndResourceTag(DEFAULT_USER_NO, resourceTag);
    if (permissions != null && !permissions.isEmpty()) {
      target.addAll(permissions);
    }
  }

  private Map<String, Object> toLegacyProject(Project project) {
    Map<String, Object> map = new HashMap<>();
    map.put("id", project.getId());
    map.put("projectId", project.getId());
    map.put("name", project.getName());
    map.put("description", project.getDescription());
    map.put("namespace", project.getNamespace());
    map.put("tag", project.getTag());
    map.put("visibility", project.getVisibility());
    map.put("config", project.getConfig());
    map.put("createOwner", getCreateOwner(project.getId()));

    JSONObject config = parseConfig(project.getConfig());
    if (config != null && !config.isEmpty()) {
      map.putAll(config);
    }
    return map;
  }

  private String getCreateOwner(Long projectId) {
    try {
      List<String> owners =
          permissionManager.getOwnerUserNameByResourceId(
              projectId, ResourceTagEnum.KNOWLEDGE_BASE.name());
      if (owners != null && !owners.isEmpty() && StringUtils.isNotBlank(owners.get(0))) {
        return owners.get(0);
      }
    } catch (Exception e) {
      log.warn("query create owner failed, projectId={}", projectId, e);
    }
    return DEFAULT_USER_NO;
  }

  private JSONObject parseConfig(String config) {
    if (StringUtils.isBlank(config)) {
      return new JSONObject();
    }
    try {
      return JSON.parseObject(config);
    } catch (Exception e) {
      log.warn("parse project config failed: {}", config, e);
      return new JSONObject();
    }
  }
}
