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

import com.antgroup.openspg.common.util.StringUtils;
import com.antgroup.openspg.core.schema.model.BasicInfo;
import com.antgroup.openspg.core.schema.model.OntologyId;
import com.antgroup.openspg.core.schema.model.alter.SchemaDraft;
import com.antgroup.openspg.core.schema.model.constraint.BaseConstraintItem;
import com.antgroup.openspg.core.schema.model.constraint.Constraint;
import com.antgroup.openspg.core.schema.model.constraint.ConstraintTypeEnum;
import com.antgroup.openspg.core.schema.model.constraint.EnumConstraint;
import com.antgroup.openspg.core.schema.model.constraint.RangeConstraint;
import com.antgroup.openspg.core.schema.model.constraint.RegularConstraint;
import com.antgroup.openspg.core.schema.model.predicate.Property;
import com.antgroup.openspg.core.schema.model.predicate.Relation;
import com.antgroup.openspg.core.schema.model.predicate.SubProperty;
import com.antgroup.openspg.core.schema.model.semantic.LogicalRule;
import com.antgroup.openspg.core.schema.model.type.BaseAdvancedType;
import com.antgroup.openspg.core.schema.model.type.BaseSPGType;
import com.antgroup.openspg.core.schema.model.type.ProjectSchema;
import com.antgroup.openspg.core.schema.model.type.SPGTypeEnum;
import com.antgroup.openspg.server.api.facade.dto.common.request.ProjectQueryRequest;
import com.antgroup.openspg.server.api.facade.dto.schema.request.SchemaAlterRequest;
import com.antgroup.openspg.server.api.http.server.BaseController;
import com.antgroup.openspg.server.api.http.server.HttpBizCallback;
import com.antgroup.openspg.server.api.http.server.HttpBizTemplate;
import com.antgroup.openspg.server.api.http.server.HttpResult;
import com.antgroup.openspg.server.biz.common.ProjectManager;
import com.antgroup.openspg.server.biz.common.util.AssertUtils;
import com.antgroup.openspg.server.biz.schema.SchemaManager;
import com.antgroup.openspg.server.biz.schema.model.NodeTypeModel;
import com.antgroup.openspg.server.biz.schema.model.SchemaCompareUtil;
import com.antgroup.openspg.server.biz.schema.model.SchemaModel;
import com.antgroup.openspg.server.biz.schema.model.SchemaModelConvertor;
import com.antgroup.openspg.server.biz.schema.model.SchemaScriptTranslateUtil;
import com.antgroup.openspg.server.common.model.project.Project;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.stream.Collectors;
import org.apache.commons.collections4.CollectionUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseBody;

/** Legacy `/v1/schemas/*` compatibility for bundled console pages. */
@Controller
@RequestMapping("/v1/schemas")
public class LegacySchemaCompatController extends BaseController {

  private static final List<SPGTypeEnum> PAGE_DISPLAY_TYPE =
      Arrays.asList(
          SPGTypeEnum.ENTITY_TYPE,
          SPGTypeEnum.EVENT_TYPE,
          SPGTypeEnum.CONCEPT_TYPE,
          SPGTypeEnum.INDEX_TYPE);
  private static final ConcurrentMap<Long, String> SCHEMA_SCRIPT_CACHE = new ConcurrentHashMap<>();

  @Autowired private SchemaManager schemaManager;
  @Autowired private ProjectManager projectManager;

  @RequestMapping(value = "/graph/{projectId}", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<Map<String, Object>> getSchemaGraph(
      @PathVariable("projectId") Long pathProjectId,
      @RequestParam(required = false) Long projectId) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Map<String, Object>>() {
          @Override
          public void check() {}

          @Override
          public Map<String, Object> action() {
            Long realProjectId = projectId == null ? pathProjectId : projectId;
            ProjectSchema schema = schemaManager.getProjectSchema(realProjectId);
            return buildGraphResponse(realProjectId, schema);
          }
        });
  }

  @RequestMapping(value = "/getSchemaNameMap", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<Map<String, String>> getSchemaNameMap(@RequestParam Long projectId) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Map<String, String>>() {
          @Override
          public void check() {}

          @Override
          public Map<String, String> action() {
            ProjectSchema schema = schemaManager.getProjectSchema(projectId);
            return buildSchemaNameMap(schema);
          }
        });
  }

  @RequestMapping(value = "/entity/{id}", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<Map<String, Object>> getEntityDetail(
      @PathVariable("id") Long id, @RequestParam(required = false) Long projectId) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Map<String, Object>>() {
          @Override
          public void check() {}

          @Override
          public Map<String, Object> action() {
            Long realProjectId = normalizeProjectId(projectId);
            ProjectSchema schema = schemaManager.getProjectSchema(realProjectId);
            Map<String, Object> node = findNodeById(id, realProjectId, schema);
            return node == null ? Collections.emptyMap() : node;
          }
        });
  }

  @RequestMapping(value = "/relation/{id}", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<Map<String, Object>> getRelationDetail(
      @PathVariable("id") Long id, @RequestParam(required = false) Long projectId) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Map<String, Object>>() {
          @Override
          public void check() {}

          @Override
          public Map<String, Object> action() {
            Long realProjectId = normalizeProjectId(projectId);
            ProjectSchema schema = schemaManager.getProjectSchema(realProjectId);
            Map<String, Object> graph = buildGraphResponse(realProjectId, schema);
            List<Map<String, Object>> edges =
                (List<Map<String, Object>>)
                    graph.getOrDefault("relationTypeDTOList", new ArrayList<>());
            for (Map<String, Object> edge : edges) {
              if (Objects.equals(id, toLong(edge.get("id")))) {
                return edge;
              }
            }
            return Collections.emptyMap();
          }
        });
  }

  @RequestMapping(value = "/tree/{projectId}", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<Map<String, Object>> getSchemaTree(
      @PathVariable("projectId") Long pathProjectId,
      @RequestParam(required = false) Long projectId) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Map<String, Object>>() {
          @Override
          public void check() {}

          @Override
          public Map<String, Object> action() {
            Long realProjectId = projectId == null ? pathProjectId : projectId;
            ProjectSchema schema = schemaManager.getProjectSchema(realProjectId);
            return buildSchemaTree(realProjectId, schema);
          }
        });
  }

  @RequestMapping(value = "/getDynamicConfig", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<Map<String, Object>> getDynamicConfig(
      @RequestParam(required = false) String type, @RequestParam(required = false) Long ids) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Map<String, Object>>() {
          @Override
          public void check() {}

          @Override
          public Map<String, Object> action() {
            Map<String, Object> result = new HashMap<>();
            result.put("type", type);
            result.put("ids", ids);
            result.put("config", Collections.emptyMap());
            return result;
          }
        });
  }

  private Long normalizeProjectId(Long projectId) {
    if (projectId != null) {
      return projectId;
    }
    ProjectQueryRequest request = new ProjectQueryRequest();
    List<Project> list = projectManager.queryPageData(request, 0, 1);
    if (CollectionUtils.isEmpty(list)) {
      return 1L;
    }
    return list.get(0).getId();
  }

  private Map<String, Object> buildGraphResponse(Long projectId, ProjectSchema schema) {
    List<BaseSPGType> spgTypes = schema == null ? Collections.emptyList() : schema.getSpgTypes();
    Map<String, BaseSPGType> typeByName =
        spgTypes.stream().collect(Collectors.toMap(BaseSPGType::getName, t -> t, (a, b) -> a));

    Map<String, Map<String, Object>> nodeByName = new LinkedHashMap<>();
    List<Map<String, Object>> entities = new ArrayList<>();
    List<Map<String, Object>> relations = new ArrayList<>();
    String belongToProjectName = getProjectName(projectId);

    for (BaseSPGType spgType : spgTypes) {
      if (!isAdvancedSchemaType(spgType.getSpgTypeEnum())) {
        continue;
      }
      Map<String, Object> node =
          toEntityTypeDTO(projectId, belongToProjectName, spgType, typeByName);
      entities.add(node);
      nodeByName.put(spgType.getName(), node);
    }

    for (BaseSPGType spgType : spgTypes) {
      if (!isAdvancedSchemaType(spgType.getSpgTypeEnum())) {
        continue;
      }
      Map<String, Object> source = nodeByName.get(spgType.getName());
      if (source == null || CollectionUtils.isEmpty(spgType.getRelations())) {
        continue;
      }
      for (Relation relation : spgType.getRelations()) {
        Map<String, Object> target = nodeByName.get(relation.getObjectTypeRef().getName());
        relations.add(toRelationTypeDTO(projectId, relation, source, target, typeByName));
      }
    }

    Map<String, Object> result = new HashMap<>();
    result.put("entityTypeDTOList", entities);
    result.put("relationTypeDTOList", relations);
    return result;
  }

  private Map<String, Object> findNodeById(Long id, Long projectId, ProjectSchema schema) {
    Map<String, Object> graph = buildGraphResponse(projectId, schema);
    List<Map<String, Object>> nodes =
        (List<Map<String, Object>>) graph.getOrDefault("entityTypeDTOList", new ArrayList<>());
    for (Map<String, Object> node : nodes) {
      if (Objects.equals(id, toLong(node.get("id")))) {
        return node;
      }
    }
    return null;
  }

  private Map<String, Object> buildSchemaTree(Long projectId, ProjectSchema schema) {
    String projectName = getProjectName(projectId);
    List<BaseSPGType> spgTypes = schema == null ? Collections.emptyList() : schema.getSpgTypes();
    List<Map<String, Object>> children = new ArrayList<>();

    for (BaseSPGType spgType : spgTypes) {
      if (!isAdvancedSchemaType(spgType.getSpgTypeEnum())) {
        continue;
      }
      Map<String, Object> schemaType = new HashMap<>();
      schemaType.put("id", resolveOntologyId(spgType.getOntologyId(), spgType.getName()));
      schemaType.put("name", spgType.getName());
      schemaType.put(
          "nameZh",
          StringUtils.isBlank(spgType.getBasicInfo().getNameZh())
              ? spgType.getName()
              : spgType.getBasicInfo().getNameZh());
      schemaType.put("belongToProject", projectId);
      schemaType.put("belongToProjectName", projectName);
      schemaType.put("entityCategory", spgType.getSpgTypeEnum().name());

      Map<String, Object> node = new HashMap<>();
      node.put("schemaType", schemaType);
      node.put("entityTypeDTO", schemaType);
      node.put("children", new ArrayList<>());
      children.add(node);
    }

    Map<String, Object> rootSchema = new HashMap<>();
    rootSchema.put("id", 0L);
    rootSchema.put("name", "Thing");
    rootSchema.put("nameZh", "事物");
    rootSchema.put("belongToProject", projectId);
    rootSchema.put("belongToProjectName", projectName);
    rootSchema.put("entityCategory", SPGTypeEnum.ENTITY_TYPE.name());

    Map<String, Object> root = new HashMap<>();
    root.put("schemaType", rootSchema);
    root.put("entityTypeDTO", rootSchema);
    root.put("children", children);
    return root;
  }

  private Map<String, String> buildSchemaNameMap(ProjectSchema schema) {
    Map<String, String> nameMap = new HashMap<>();
    if (schema == null || CollectionUtils.isEmpty(schema.getSpgTypes())) {
      return nameMap;
    }
    for (BaseSPGType spgType : schema.getSpgTypes()) {
      String typeName = spgType.getName();
      String typeZh = safeZh(spgType.getBasicInfo(), typeName);
      nameMap.put(typeName, typeZh);
      nameMap.put(shortName(typeName), typeZh);

      if (CollectionUtils.isNotEmpty(spgType.getProperties())) {
        for (Property property : spgType.getProperties()) {
          String propertyName = property.getName();
          String propertyZh = safeZh(property.getBasicInfo(), propertyName);
          nameMap.put(propertyName, propertyZh);
          nameMap.put(typeName + "." + propertyName, propertyZh);
          for (SubProperty subProperty : property.getSubProperties()) {
            String subName = subProperty.getName();
            String subZh = safeZh(subProperty.getBasicInfo(), subName);
            nameMap.put(typeName + "_" + propertyName + "." + subName, subZh);
          }
        }
      }

      if (CollectionUtils.isNotEmpty(spgType.getRelations())) {
        for (Relation relation : spgType.getRelations()) {
          String relationName = relation.getName();
          String relationZh = safeZh(relation.getBasicInfo(), relationName);
          nameMap.put(relationName, relationZh);
          nameMap.put(typeName + "." + relationName, relationZh);
        }
      }
    }
    return nameMap;
  }

  private Map<String, Object> toEntityTypeDTO(
      Long projectId,
      String projectName,
      BaseSPGType spgType,
      Map<String, BaseSPGType> typeByName) {
    Map<String, Object> map = new HashMap<>();
    Long id = resolveOntologyId(spgType.getOntologyId(), spgType.getName());
    map.put("id", id);
    map.put("originId", id);
    map.put("name", spgType.getName());
    map.put("nameZh", safeZh(spgType.getBasicInfo(), spgType.getName()));
    map.put(
        "description", spgType.getBasicInfo() == null ? null : spgType.getBasicInfo().getDesc());
    map.put("entityCategory", spgType.getSpgTypeEnum().name());
    map.put("schemaEntityCategoryEnum", spgType.getSpgTypeEnum().name());
    map.put("belongToProject", projectId);
    map.put("belongToProjectName", projectName);
    map.put("fromCoreKg", false);
    map.put("propertyList", toPropertyList(spgType, typeByName, false));
    map.put("inheritedPropertyList", toPropertyList(spgType, typeByName, true));
    return map;
  }

  private List<Map<String, Object>> toPropertyList(
      BaseSPGType spgType, Map<String, BaseSPGType> typeByName, boolean inherited) {
    if (CollectionUtils.isEmpty(spgType.getProperties())) {
      return new ArrayList<>();
    }
    List<Map<String, Object>> result = new ArrayList<>();
    for (Property property : spgType.getProperties()) {
      boolean isInherited = Boolean.TRUE.equals(property.getInherited());
      if (isInherited != inherited) {
        continue;
      }
      Map<String, Object> item = new HashMap<>();
      Long id =
          resolveOntologyId(
              property.getOntologyId(), spgType.getName() + "." + property.getName() + "@property");
      item.put("id", id);
      item.put("name", property.getName());
      item.put("nameZh", safeZh(property.getBasicInfo(), property.getName()));
      item.put(
          "description",
          property.getBasicInfo() == null ? null : property.getBasicInfo().getDesc());
      item.put("inherited", isInherited);
      item.put(
          "rangeName",
          property.getObjectTypeRef() == null ? null : property.getObjectTypeRef().getName());
      item.put("rangeNameZh", resolveTypeZh(typeByName, property.getObjectTypeRef()));
      item.put(
          "rangeEntityName",
          property.getObjectTypeRef() == null ? null : property.getObjectTypeRef().getName());
      item.put("rangeEntityNameZh", resolveTypeZh(typeByName, property.getObjectTypeRef()));
      item.put("logicRuleDTO", toLogicalRuleDTO(property.getLogicalRule()));
      item.put("constraints", toConstraintDTOs(property.getConstraint()));
      item.put("propertyList", toSubPropertyList(spgType, property));
      result.add(item);
    }
    return result;
  }

  private List<Map<String, Object>> toSubPropertyList(BaseSPGType spgType, Property property) {
    if (CollectionUtils.isEmpty(property.getSubProperties())) {
      return new ArrayList<>();
    }
    List<Map<String, Object>> result = new ArrayList<>();
    for (SubProperty subProperty : property.getSubProperties()) {
      Map<String, Object> item = new HashMap<>();
      Long id =
          resolveOntologyId(
              subProperty.getOntologyId(),
              spgType.getName() + "." + property.getName() + "." + subProperty.getName());
      item.put("id", id);
      item.put("name", subProperty.getName());
      item.put("nameZh", safeZh(subProperty.getBasicInfo(), subProperty.getName()));
      item.put(
          "description",
          subProperty.getBasicInfo() == null ? null : subProperty.getBasicInfo().getDesc());
      item.put("inherited", false);
      item.put(
          "rangeName",
          subProperty.getObjectTypeRef() == null ? null : subProperty.getObjectTypeRef().getName());
      result.add(item);
    }
    return result;
  }

  private Map<String, Object> toRelationTypeDTO(
      Long projectId,
      Relation relation,
      Map<String, Object> source,
      Map<String, Object> target,
      Map<String, BaseSPGType> typeByName) {
    Map<String, Object> map = new HashMap<>();
    Long sourceId = toLong(source.get("id"));
    String sourceName = String.valueOf(source.get("name"));
    String sourceNameZh = String.valueOf(source.get("nameZh"));
    Long targetId =
        target == null
            ? resolveOntologyId((OntologyId) null, relation.getObjectTypeRef().getName())
            : toLong(target.get("id"));
    String targetName =
        target == null ? relation.getObjectTypeRef().getName() : String.valueOf(target.get("name"));
    String targetNameZh =
        target == null
            ? resolveTypeZh(typeByName, relation.getObjectTypeRef())
            : String.valueOf(target.get("nameZh"));

    Long relationId =
        resolveOntologyId(
            relation.getOntologyId(),
            sourceName + "." + relation.getName() + "." + targetName + "@relation");
    map.put("id", relationId);
    map.put("originId", relationId);
    map.put("name", relation.getName());
    map.put("type", relation.getName());
    map.put("nameZh", safeZh(relation.getBasicInfo(), relation.getName()));
    map.put("typeZh", safeZh(relation.getBasicInfo(), relation.getName()));
    map.put(
        "description", relation.getBasicInfo() == null ? null : relation.getBasicInfo().getDesc());
    map.put("direction", "SINGLE");
    map.put("source", String.valueOf(sourceId));
    map.put("sourceName", sourceName);
    map.put("sourceNameZh", sourceNameZh);
    map.put("target", String.valueOf(targetId));
    map.put("targetName", targetName);
    map.put("targetNameZh", targetNameZh);
    map.put(
        "startEntity",
        buildTypeRefDTO(sourceId, sourceName, sourceNameZh, projectId, getProjectName(projectId)));
    map.put(
        "endEntity",
        buildTypeRefDTO(targetId, targetName, targetNameZh, projectId, getProjectName(projectId)));
    map.put("logicRuleDTO", toLogicalRuleDTO(relation.getLogicalRule()));
    map.put("propertyList", toRelationPropertyList(relation));
    map.put("inheritedPropertyList", new ArrayList<>());
    map.put("fromCoreKg", false);
    return map;
  }

  private List<Map<String, Object>> toRelationPropertyList(Relation relation) {
    if (CollectionUtils.isEmpty(relation.getSubProperties())) {
      return new ArrayList<>();
    }
    List<Map<String, Object>> result = new ArrayList<>();
    for (SubProperty subProperty : relation.getSubProperties()) {
      Map<String, Object> item = new HashMap<>();
      Long id =
          resolveOntologyId(
              subProperty.getOntologyId(),
              relation.getName() + "." + subProperty.getName() + "@relationProperty");
      item.put("id", id);
      item.put("name", subProperty.getName());
      item.put("nameZh", safeZh(subProperty.getBasicInfo(), subProperty.getName()));
      item.put(
          "description",
          subProperty.getBasicInfo() == null ? null : subProperty.getBasicInfo().getDesc());
      result.add(item);
    }
    return result;
  }

  private Map<String, Object> buildTypeRefDTO(
      Long id, String name, String nameZh, Long projectId, String projectName) {
    Map<String, Object> ref = new HashMap<>();
    ref.put("id", id);
    ref.put("name", name);
    ref.put("nameZh", nameZh);
    ref.put("belongToProject", projectId);
    ref.put("belongToProjectName", projectName);
    return ref;
  }

  private List<Map<String, Object>> toConstraintDTOs(Constraint constraint) {
    if (constraint == null || CollectionUtils.isEmpty(constraint.getConstraintItems())) {
      return new ArrayList<>();
    }
    List<Map<String, Object>> result = new ArrayList<>();
    for (BaseConstraintItem item : constraint.getConstraintItems()) {
      if (item == null) {
        continue;
      }
      ConstraintTypeEnum type = item.getConstraintTypeEnum();
      if (type == null) {
        continue;
      }
      switch (type) {
        case UNIQUE:
          result.add(constraintItem("UNIQUE", "唯一"));
          break;
        case NOT_NULL:
          result.add(constraintItem("REQUIRE", "非空"));
          break;
        case MULTI_VALUE:
          result.add(constraintItem("MULTIVALUE", "多值"));
          break;
        case ENUM:
          Map<String, Object> enumItem = constraintItem("ENUM", "枚举");
          if (item instanceof EnumConstraint) {
            enumItem.put("value", ((EnumConstraint) item).getEnumValues());
          }
          result.add(enumItem);
          break;
        case REGULAR:
          Map<String, Object> regularItem = constraintItem("REGULAR", "正则");
          if (item instanceof RegularConstraint) {
            regularItem.put("value", ((RegularConstraint) item).getRegularPattern());
          }
          result.add(regularItem);
          break;
        case RANGE:
          if (item instanceof RangeConstraint) {
            RangeConstraint range = (RangeConstraint) item;
            if (StringUtils.isNotBlank(range.getMinimumValue())) {
              String id = Boolean.TRUE.equals(range.getLeftOpen()) ? "MINIMUM_GT" : "MINIMUM_GT_OE";
              Map<String, Object> minItem = constraintItem(id, "最小值");
              minItem.put("value", range.getMinimumValue());
              result.add(minItem);
            }
            if (StringUtils.isNotBlank(range.getMaximumValue())) {
              String id =
                  Boolean.TRUE.equals(range.getRightOpen()) ? "MAXIMUM_LT" : "MAXIMUM_LT_OE";
              Map<String, Object> maxItem = constraintItem(id, "最大值");
              maxItem.put("value", range.getMaximumValue());
              result.add(maxItem);
            }
          }
          break;
        default:
          break;
      }
    }
    return result;
  }

  private Map<String, Object> constraintItem(String id, String nameZh) {
    Map<String, Object> map = new HashMap<>();
    map.put("id", id);
    map.put("name", id);
    map.put("nameZh", nameZh);
    return map;
  }

  private Map<String, Object> toLogicalRuleDTO(LogicalRule rule) {
    if (rule == null || StringUtils.isBlank(rule.getContent())) {
      return null;
    }
    Map<String, Object> map = new HashMap<>();
    map.put("expression", rule.getContent());
    map.put("content", rule.getContent());
    map.put("name", rule.getName());
    map.put("version", rule.getVersion());
    return map;
  }

  private String resolveTypeZh(
      Map<String, BaseSPGType> typeByName,
      com.antgroup.openspg.core.schema.model.type.SPGTypeRef ref) {
    if (ref == null || StringUtils.isBlank(ref.getName())) {
      return null;
    }
    BaseSPGType targetType = typeByName.get(ref.getName());
    if (targetType != null) {
      return safeZh(targetType.getBasicInfo(), targetType.getName());
    }
    return shortName(ref.getName());
  }

  private String safeZh(BasicInfo<?> basicInfo, String defaultVal) {
    if (basicInfo == null || StringUtils.isBlank(basicInfo.getNameZh())) {
      return shortName(defaultVal);
    }
    return basicInfo.getNameZh();
  }

  private String shortName(String name) {
    if (StringUtils.isBlank(name)) {
      return name;
    }
    int idx = name.lastIndexOf('.');
    return idx >= 0 && idx + 1 < name.length() ? name.substring(idx + 1) : name;
  }

  private Long resolveOntologyId(OntologyId ontologyId, String fallbackKey) {
    if (ontologyId != null && ontologyId.getUniqueId() != null) {
      return ontologyId.getUniqueId();
    }
    long hash = Math.abs((fallbackKey == null ? "unknown" : fallbackKey).hashCode());
    return hash == 0 ? 1L : hash;
  }

  private Long toLong(Object v) {
    if (v instanceof Long) {
      return (Long) v;
    }
    if (v instanceof Integer) {
      return ((Integer) v).longValue();
    }
    if (v == null) {
      return null;
    }
    try {
      return Long.parseLong(String.valueOf(v));
    } catch (Exception e) {
      return null;
    }
  }

  private boolean isAdvancedSchemaType(SPGTypeEnum spgTypeEnum) {
    if (spgTypeEnum == null) {
      return false;
    }
    return !SPGTypeEnum.BASIC_TYPE.equals(spgTypeEnum);
  }

  private String getProjectName(Long projectId) {
    Project project = projectManager.queryById(projectId);
    return project == null ? "" : project.getName();
  }

  @RequestMapping(value = "", method = RequestMethod.POST)
  @ResponseBody
  public HttpResult<Boolean> saveSchemaScript(
      @RequestBody(required = false) Map<String, Object> body) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<Boolean>() {
          @Override
          public void check() {
            AssertUtils.assertParamObjectIsNotNull("requestBody", body);
          }

          @Override
          public Boolean action() {
            Long projectId = extractProjectId(body);
            Project project = projectManager.queryById(projectId);
            AssertUtils.assertParamObjectIsNotNull("project", project);

            String schemaScript = extractSchemaScript(body);
            if (StringUtils.isBlank(schemaScript)) {
              return false;
            }
            String normalizedSchemaScript =
                withProjectNamespace(project.getNamespace(), schemaScript).trim() + "\n";

            SchemaDraft schemaDraft = buildSchemaDraftByScript(project, normalizedSchemaScript);
            if (schemaDraft == null || CollectionUtils.isEmpty(schemaDraft.getAlterSpgTypes())) {
              SCHEMA_SCRIPT_CACHE.put(projectId, normalizedSchemaScript);
              return true;
            }

            SchemaAlterRequest request = new SchemaAlterRequest();
            request.setProjectId(projectId);
            request.setSchemaDraft(schemaDraft);
            schemaManager.alterSchema(request);
            SCHEMA_SCRIPT_CACHE.put(projectId, normalizedSchemaScript);
            return true;
          }
        });
  }

  private SchemaDraft buildSchemaDraftByScript(Project project, String rawScript) {
    String script = withProjectNamespace(project.getNamespace(), rawScript);
    SchemaModel schemaModel = SchemaScriptTranslateUtil.translateScript(script);
    ProjectSchema projectSchema = schemaManager.getProjectSchema(project.getId());

    List<NodeTypeModel> oldNodeTypeModels = new ArrayList<>();
    if (projectSchema != null && CollectionUtils.isNotEmpty(projectSchema.getSpgTypes())) {
      for (BaseSPGType spgType : projectSchema.getSpgTypes()) {
        if (!(spgType instanceof BaseAdvancedType)
            || !PAGE_DISPLAY_TYPE.contains(spgType.getSpgTypeEnum())) {
          continue;
        }
        oldNodeTypeModels.add(
            SchemaModelConvertor.convert2NodeTypeModel(
                project.getNamespace(), (BaseAdvancedType) spgType));
      }
    }

    List<NodeTypeModel> nodeTypeModels =
        schemaModel.getNodeTypeModels() == null
            ? new ArrayList<>()
            : new ArrayList<>(schemaModel.getNodeTypeModels());
    Set<String> nameSet =
        nodeTypeModels.stream().map(NodeTypeModel::getName).collect(Collectors.toSet());
    for (NodeTypeModel model : oldNodeTypeModels) {
      if (!nameSet.contains(model.getName())) {
        nodeTypeModels.add(model);
      }
    }

    SchemaCompareUtil.SchemaChangeDTO changeDTO =
        new SchemaCompareUtil()
            .compare(schemaModel.getNamespace(), oldNodeTypeModels, nodeTypeModels);
    List<BaseAdvancedType> alterTypes = new ArrayList<>();
    if (CollectionUtils.isNotEmpty(changeDTO.getAddTypes())) {
      alterTypes.addAll(changeDTO.getAddTypes());
    }
    if (CollectionUtils.isNotEmpty(changeDTO.getUpdateTypes())) {
      alterTypes.addAll(changeDTO.getUpdateTypes());
    }

    SchemaDraft schemaDraft = new SchemaDraft();
    schemaDraft.setAlterSpgTypes(alterTypes);
    return schemaDraft;
  }

  private String withProjectNamespace(String namespace, String rawScript) {
    String script = rawScript == null ? "" : rawScript.trim();
    if (StringUtils.isBlank(script)) {
      return "namespace " + namespace;
    }
    List<String> lines = Arrays.asList(script.replace("\r\n", "\n").split("\n"));
    List<String> normalized = new ArrayList<>();
    boolean namespaceSkipped = false;
    for (String line : lines) {
      String trimmed = line == null ? "" : line.trim();
      if (!namespaceSkipped && trimmed.startsWith("namespace ")) {
        namespaceSkipped = true;
        continue;
      }
      normalized.add(line);
    }
    String body = normalized.stream().collect(Collectors.joining("\n")).trim();
    if (StringUtils.isBlank(body)) {
      return "namespace " + namespace;
    }
    return "namespace " + namespace + "\n\n" + body + "\n";
  }

  private Long extractProjectId(Map<String, Object> body) {
    Long projectId = toLong(body.get("projectId"));
    if (projectId == null) {
      projectId = toLong(body.get("project_id"));
    }
    if (projectId == null) {
      projectId = toLong(body.get("id"));
    }
    if (projectId == null) {
      projectId = normalizeProjectId(null);
    }
    return projectId;
  }

  private String extractSchemaScript(Map<String, Object> body) {
    String[] keys = new String[] {"schemaScript", "schema_script", "schema", "script", "content"};
    for (String key : keys) {
      Object value = body.get(key);
      if (!(value instanceof String)) {
        continue;
      }
      String text = ((String) value).trim();
      if (StringUtils.isNotBlank(text)) {
        return text;
      }
    }
    return null;
  }

  @RequestMapping(value = "/getSchemaScript", method = RequestMethod.GET)
  @ResponseBody
  public HttpResult<String> getSchemaScript(@RequestParam Long projectId) {
    return HttpBizTemplate.execute2(
        new HttpBizCallback<String>() {
          @Override
          public void check() {}

          @Override
          public String action() {
            String script = SCHEMA_SCRIPT_CACHE.get(projectId);
            if (StringUtils.isNotBlank(script)) {
              return script;
            }
            Project project = projectManager.queryById(projectId);
            String namespace = project == null ? "default" : project.getNamespace();
            return "// Legacy compatibility mode: schema script cache is empty. "
                + "Please apply schema once via POST /v1/schemas.\n"
                + "namespace "
                + namespace
                + "\n";
          }
        });
  }
}
