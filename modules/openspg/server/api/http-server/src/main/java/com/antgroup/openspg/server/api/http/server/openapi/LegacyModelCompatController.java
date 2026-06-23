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
import com.antgroup.openspg.common.util.StringUtils;
import com.antgroup.openspg.server.api.http.server.BaseController;
import com.antgroup.openspg.server.api.http.server.HttpBizCallback;
import com.antgroup.openspg.server.api.http.server.HttpBizTemplate;
import com.antgroup.openspg.server.api.http.server.HttpResult;
import com.antgroup.openspg.server.biz.common.ModelProviderManager;
import com.antgroup.openspg.server.biz.common.ProviderParamManager;
import com.antgroup.openspg.server.biz.common.UserModelManager;
import com.antgroup.openspg.server.common.model.account.Account;
import com.antgroup.openspg.server.common.model.provider.ModelProvider;
import com.antgroup.openspg.server.common.model.providerparam.ProviderParam;
import com.antgroup.openspg.server.common.model.usermodel.UserModel;
import com.antgroup.openspg.server.common.model.usermodel.UserModelDTO;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import org.apache.commons.collections4.CollectionUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseBody;

/** Legacy `/v1/model/*` compatibility for bundled console pages. */
@Controller
@RequestMapping("/v1/model")
public class LegacyModelCompatController extends BaseController {

  private static final String DEFAULT_USER_NO = "openspg";

  @Autowired private UserModelManager userModelManager;
  @Autowired private ModelProviderManager modelProviderManager;
  @Autowired private ProviderParamManager providerParamManager;

  @RequestMapping(
      value = {"/list/{modelType}", "/list/{modelType}/"},
      method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<List<Map<String, Object>>> listByType(
      @PathVariable("modelType") String modelType,
      @RequestParam(required = false) String queryStr,
      @RequestParam(required = false) String modelId,
      @RequestParam(required = false) String userNo) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<List<Map<String, Object>>>() {
          @Override
          public void check() {}

          @Override
          public List<Map<String, Object>> action() {
            String realUserNo = StringUtils.isBlank(userNo) ? getCurrentUserNo() : userNo;
            List<Map<String, Object>> result =
                userModelManager.list(modelType, queryStr, modelId, realUserNo);
            return result == null ? Collections.emptyList() : result;
          }
        });
  }

  @RequestMapping(
      value = {"/list", "/list/"},
      method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<List<Map<String, Object>>> listAll(
      @RequestParam(required = false) String queryStr,
      @RequestParam(required = false) String modelId,
      @RequestParam(required = false) String userNo) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<List<Map<String, Object>>>() {
          @Override
          public void check() {}

          @Override
          public List<Map<String, Object>> action() {
            String realUserNo = StringUtils.isBlank(userNo) ? getCurrentUserNo() : userNo;
            List<Map<String, Object>> result =
                userModelManager.list(null, queryStr, modelId, realUserNo);
            return result == null ? Collections.emptyList() : result;
          }
        });
  }

  @RequestMapping(
      value = {"/provider", "/provider/"},
      method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<List<ModelProvider>> providerList(
      @RequestParam(required = false) String modelType) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<List<ModelProvider>>() {
          @Override
          public void check() {}

          @Override
          public List<ModelProvider> action() {
            List<ModelProvider> result = modelProviderManager.query(modelType);
            return result == null ? Collections.emptyList() : result;
          }
        });
  }

  @RequestMapping(value = "/provider/{provider}/{modelType}", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<ProviderParam> providerParam(
      @PathVariable("provider") String provider, @PathVariable("modelType") String modelType) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<ProviderParam>() {
          @Override
          public void check() {}

          @Override
          public ProviderParam action() {
            ProviderParam param =
                providerParamManager.getByProviderAndModelType(provider, modelType);
            if (param == null) {
              ProviderParam empty = new ProviderParam();
              empty.setProvider(provider);
              empty.setModelType(modelType);
              empty.setModel(Collections.emptyList());
              return empty;
            }
            if (CollectionUtils.isEmpty(param.getModel())) {
              param.setModel(Collections.emptyList());
            }
            return param;
          }
        });
  }

  @RequestMapping(value = "/apikey", method = RequestMethod.PUT)
  @ResponseBody
  public HttpResult<Long> updateApiKey(@RequestBody(required = false) Map<String, Object> body) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Long>() {
          @Override
          public void check() {}

          @Override
          public Long action() {
            UserModelDTO request = toUserModelDTO(body);
            request.setUserNo(firstNonBlank(request.getUserNo(), getCurrentUserNo()));
            if (request.getConfig() == null) {
              request.setConfig(new JSONObject());
            }
            return userModelManager.updateApiKey(request);
          }
        });
  }

  @RequestMapping(value = "", method = RequestMethod.POST)
  @ResponseBody
  public HttpResult<Long> addUserModel(@RequestBody(required = false) Map<String, Object> body) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Long>() {
          @Override
          public void check() {}

          @Override
          public Long action() {
            UserModelDTO request = toUserModelDTO(body);
            request.setUserNo(firstNonBlank(request.getUserNo(), getCurrentUserNo()));
            if (request.getConfig() == null) {
              request.setConfig(new JSONObject());
            }
            return userModelManager.insert(request, userModelManager.getModelTypeMap());
          }
        });
  }

  @RequestMapping(value = "", method = RequestMethod.PUT)
  @ResponseBody
  public HttpResult<Long> updateUserModel(@RequestBody(required = false) Map<String, Object> body) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Long>() {
          @Override
          public void check() {}

          @Override
          public Long action() {
            UserModelDTO request = toUserModelDTO(body);
            String userNo = firstNonBlank(request.getUserNo(), getCurrentUserNo());
            request.setUserNo(userNo);
            List<UserModel> models =
                userModelManager.getByProviderAndName(request.getProvider(), request.getName());
            if (CollectionUtils.isEmpty(models)) {
              return 0L;
            }
            List<Long> ids = new ArrayList<>();
            for (UserModel model : models) {
              if (StringUtils.equals(userNo, model.getUserNo())
                  || StringUtils.equals(DEFAULT_USER_NO, model.getUserNo())) {
                ids.add(model.getId());
              }
            }
            if (ids.isEmpty()) {
              return 0L;
            }
            String config =
                request.getCustomize() == null ? null : request.getCustomize().toJSONString();
            String newName = firstNonBlank(request.getNewName(), request.getName());
            return userModelManager.updateBaseInfoByIds(
                ids, newName, request.getVisibility(), userNo, config);
          }
        });
  }

  @RequestMapping(value = "/{provider}/{name}", method = RequestMethod.DELETE)
  @ResponseBody
  public HttpResult<Boolean> deleteProviderModel(
      @PathVariable("provider") String provider,
      @PathVariable("name") String name,
      @RequestParam(required = false) String modelId) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Boolean>() {
          @Override
          public void check() {}

          @Override
          public Boolean action() {
            if (StringUtils.isNotBlank(modelId)) {
              JSONObject modelInfo = userModelManager.getByModelId(modelId);
              if (modelInfo != null && modelInfo.getLong("id") != null) {
                return userModelManager.deleteModel(modelInfo.getLong("id"), modelId);
              }
            }
            String userNo = getCurrentUserNo();
            List<UserModel> models = userModelManager.getByProviderAndName(provider, name);
            if (CollectionUtils.isEmpty(models)) {
              return true;
            }
            List<Long> ids = new ArrayList<>();
            for (UserModel model : models) {
              if (StringUtils.equals(userNo, model.getUserNo())
                  || StringUtils.equals(DEFAULT_USER_NO, model.getUserNo())) {
                ids.add(model.getId());
              }
            }
            if (ids.isEmpty()) {
              return false;
            }
            return userModelManager.deleteByIds(ids) > 0;
          }
        });
  }

  @RequestMapping(value = "/{modelId}", method = RequestMethod.PUT)
  @ResponseBody
  public HttpResult<Boolean> updateModelVisibility(
      @PathVariable("modelId") String modelId,
      @RequestParam(required = false) String visibility,
      @RequestBody(required = false) Map<String, Object> customize) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Boolean>() {
          @Override
          public void check() {}

          @Override
          public Boolean action() {
            JSONObject customizeJson =
                customize == null ? null : JSON.parseObject(JSON.toJSONString(customize));
            return userModelManager.updateModelVisibility(modelId, visibility, customizeJson);
          }
        });
  }

  private UserModelDTO toUserModelDTO(Map<String, Object> body) {
    if (body == null) {
      return new UserModelDTO();
    }
    UserModelDTO dto = JSON.parseObject(JSON.toJSONString(body), UserModelDTO.class);
    if (dto.getConfig() == null && body.get("config") instanceof Map) {
      dto.setConfig(JSON.parseObject(JSON.toJSONString(body.get("config"))));
    }
    if (dto.getCustomize() == null && body.get("customize") instanceof Map) {
      dto.setCustomize(JSON.parseObject(JSON.toJSONString(body.get("customize"))));
    }
    return dto;
  }

  private String firstNonBlank(String left, String right) {
    return StringUtils.isNotBlank(left) ? left : right;
  }

  private String getCurrentUserNo() {
    Account account = null;
    try {
      account = getLoginAccount();
    } catch (Exception ignore) {
      // ignore
    }
    if (account == null || StringUtils.isBlank(account.getWorkNo())) {
      return DEFAULT_USER_NO;
    }
    return account.getWorkNo();
  }
}
