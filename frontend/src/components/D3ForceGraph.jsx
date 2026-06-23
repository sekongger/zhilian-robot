import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { Card, Switch, Space, Tooltip, Button, Tag } from 'antd';
import { FullscreenOutlined, FullscreenExitOutlined, FireOutlined } from '@ant-design/icons';

const D3ForceGraph = ({
  data,
  onNodeClick,
  title = null,
  compact = false,
  height = 600,
  showLegend = true,
  allowFullscreen = true,
}) => {
  const svgRef = useRef(null);
  const wrapperRef = useRef(null);
  const containerRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [showEdgeLabels, setShowEdgeLabels] = useState(true);
  const [showMomentum, setShowMomentum] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const COLOR_MAP = {
    'companies': '#3b82f6',
    'COMPANY': '#3b82f6',
    'products': '#10b981',
    'PRODUCT': '#10b981',
    'technologies': '#f59e0b',
    'TECHNOLOGY': '#f59e0b',
    'persons': '#ef4444',
    'PERSON': '#ef4444',
    'locations': '#06b6d4',
    'LOCATION': '#06b6d4',
    'organizations': '#8b5cf6',
    'unknown': '#94a3b8'
  };

  // 动量颜色映射（修复数据类型和边界处理）
  const getMomentumColor = (momentum) => {
    // 数据验证和类型转换
    if (momentum === undefined || momentum === null) {
      console.debug('[D3ForceGraph] 动量值为空，使用默认颜色');
      return COLOR_MAP.unknown;
    }
    
    // 确保转换为数字类型
    const m = parseFloat(momentum);
    if (isNaN(m)) {
      console.warn('[D3ForceGraph] 动量值无法解析为数字:', momentum);
      return COLOR_MAP.unknown;
    }
    
    // 归一化到[0, 1]并记录异常值
    const normalized = Math.max(0, Math.min(1, m));
    if (m < 0 || m > 1) {
      console.warn('[D3ForceGraph] 动量值超出范围[0,1]:', m, '已归一化为:', normalized);
    }
    
    // 颜色映射（4级渐变：蓝→绿→橙→红）
    if (normalized < 0.3) return '#3b82f6'; // 蓝色 - 低动量
    if (normalized < 0.5) return '#10b981'; // 绿色 - 中低
    if (normalized < 0.7) return '#f59e0b'; // 橙色 - 中高
    return '#ef4444'; // 红色 - 高动量
  };

  // 计算节点半径（基于动量，增强数据验证）
  const getNodeRadius = (node) => {
    const baseRadius = 12;
    if (!showMomentum) return baseRadius;
    
    const momentum = parseFloat(node.current_momentum);
    if (isNaN(momentum) || momentum <= 0) return baseRadius;
    
    // 半径随动量线性增长：12px - 30px
    const normalizedMomentum = Math.max(0, Math.min(1, momentum));
    return baseRadius + (normalizedMomentum * 18);
  };

  // 处理全屏切换
  const toggleFullscreen = () => {
    if (!containerRef.current) return;

    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().then(() => {
        setIsFullscreen(true);
        setTimeout(() => updateDimensions(), 100);
      }).catch(err => console.error('无法进入全屏:', err));
    } else {
      document.exitFullscreen().then(() => {
        setIsFullscreen(false);
        setTimeout(() => updateDimensions(), 100);
      });
    }
  };

  // 监听全屏变化
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
      setTimeout(() => updateDimensions(), 100);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  const updateDimensions = () => {
    if (wrapperRef.current) {
      setDimensions({
        width: wrapperRef.current.clientWidth,
        height: wrapperRef.current.clientHeight
      });
    }
  };

  useEffect(() => {
    window.addEventListener('resize', updateDimensions);
    updateDimensions();
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  useEffect(() => {
    if (!data || !svgRef.current || !data.nodes || data.nodes.length === 0) return;

    // 深拷贝数据
    const nodes = data.nodes.map(d => ({ ...d }));
    const nodeIds = new Set(nodes.map(d => d.id));
    const rawLinks = data.edges ? data.edges.map(d => ({ ...d })) : [];
    const links = rawLinks.filter((d) => {
      const sourceId = d?.source?.id || d?.source;
      const targetId = d?.target?.id || d?.target;
      return nodeIds.has(sourceId) && nodeIds.has(targetId);
    });
    if (rawLinks.length !== links.length) {
      console.warn('[D3ForceGraph] 发现孤儿边，已自动过滤:', rawLinks.length - links.length);
    }

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const { width, height } = dimensions;

    // 创建主组
    const g = svg.append("g");

    // 缩放行为
    const zoom = d3.zoom()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });
    svg.call(zoom);

    // 力导向模拟
    const simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links)
        .id(d => d.id)
        .distance(200))
      .force("charge", d3.forceManyBody().strength(-800))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide().radius(40));

    // 箭头标记（支持动量渐变）
    const defs = svg.append("defs");
    
    // 默认箭头
    defs.selectAll("marker")
      .data(["end"])
      .enter().append("marker")
      .attr("id", "arrow")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 30)
      .attr("refY", 0)
      .attr("markerWidth", 8)
      .attr("markerHeight", 8)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#64748b");
    
    // 为每条边创建动量渐变色（如果启用动量显示）
    if (showMomentum) {
      defs.selectAll("linearGradient")
        .data(links)
        .enter().append("linearGradient")
        .attr("id", (d, i) => `gradient-${i}`)
        .attr("gradientUnits", "userSpaceOnUse")
        .attr("x1", d => {
          const source = nodes.find(n => n.id === d.source.id || n.id === d.source);
          return source ? source.x || 0 : 0;
        })
        .attr("y1", d => {
          const source = nodes.find(n => n.id === d.source.id || n.id === d.source);
          return source ? source.y || 0 : 0;
        })
        .attr("x2", d => {
          const target = nodes.find(n => n.id === d.target.id || n.id === d.target);
          return target ? target.x || 0 : 0;
        })
        .attr("y2", d => {
          const target = nodes.find(n => n.id === d.target.id || n.id === d.target);
          return target ? target.y || 0 : 0;
        })
        .each(function(d) {
          const source = nodes.find(n => n.id === d.source.id || n.id === d.source);
          const target = nodes.find(n => n.id === d.target.id || n.id === d.target);
          
          const sourceColor = source?.current_momentum !== undefined 
            ? getMomentumColor(source.current_momentum) 
            : '#64748b';
          const targetColor = target?.current_momentum !== undefined 
            ? getMomentumColor(target.current_momentum) 
            : '#64748b';
          
          d3.select(this).append("stop")
            .attr("offset", "0%")
            .attr("stop-color", sourceColor)
            .attr("stop-opacity", 0.6);
          
          d3.select(this).append("stop")
            .attr("offset", "100%")
            .attr("stop-color", targetColor)
            .attr("stop-opacity", 0.6);
        });
    }

    // 渲染连线（支持动量渐变）
    const link = g.append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", (d, i) => showMomentum ? `url(#gradient-${i})` : "#475569")
      .attr("stroke-opacity", showMomentum ? 1 : 0.6)
      .attr("stroke-width", 2)
      .attr("marker-end", "url(#arrow)");

    // 连线标签
    const linkLabel = g.append("g")
      .selectAll("text")
      .data(links)
      .join("text")
      .attr("dy", -8)
      .attr("text-anchor", "middle")
      .attr("fill", "#94a3b8")
      .attr("font-size", "11px")
      .attr("opacity", showEdgeLabels ? 1 : 0)
      .text(d => d.relation || d.relationship || '');

    // 渲染节点
    const node = g.append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended))
      .on("click", (event, d) => {
        if (onNodeClick) onNodeClick(d);
      });

    // 节点圆圈
    node.append("circle")
      .attr("r", d => getNodeRadius(d))
      .attr("fill", d => showMomentum && d.current_momentum !== undefined 
        ? getMomentumColor(d.current_momentum)
        : (COLOR_MAP[d.type] || COLOR_MAP.unknown))
      .attr("stroke", "#fff")
      .attr("stroke-width", 2)
      .attr("cursor", "pointer")
      .attr("opacity", 0.9)
      .on("mouseover", function(event, d) {
        d3.select(this)
          .transition()
          .duration(200)
          .attr("r", getNodeRadius(d) + 5)
          .attr("opacity", 1);
        
        // 显示Tooltip（如果有动量信息）
        if (showMomentum && d.current_momentum !== undefined) {
          const tooltip = d3.select("body").append("div")
            .attr("class", "d3-tooltip")
            .style("position", "absolute")
            .style("background", "#1e293b")
            .style("border", "1px solid #334155")
            .style("border-radius", "6px")
            .style("padding", "8px 12px")
            .style("color", "#e2e8f0")
            .style("font-size", "12px")
            .style("pointer-events", "none")
            .style("z-index", "10000")
            .html(`
              <div><strong>${d.name}</strong></div>
              <div style="margin-top: 4px;">动量: ${(d.current_momentum * 100).toFixed(1)}%</div>
              ${d.reference_count ? `<div>引用: ${d.reference_count}次</div>` : ''}
            `)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 28) + "px");
          
          d3.select(this).on("mouseout", function() {
            tooltip.remove();
            d3.select(this)
              .transition()
              .duration(200)
              .attr("r", getNodeRadius(d))
              .attr("opacity", 0.9);
          });
        }
      })
      .on("mouseout", function() {
        d3.selectAll(".d3-tooltip").remove();
        d3.select(this)
          .transition()
          .duration(200)
          .attr("r", getNodeRadius(d))
          .attr("opacity", 0.9);
      });
    
    // 高级动量可视化效果
    if (showMomentum) {
      
      // 1. 高动量节点光环效果（脉动）- 降低阈值到0.6
      const highMomentumNodes = node.filter(d => d.current_momentum && d.current_momentum > 0.6);
      
      highMomentumNodes.append("circle")
        .attr("class", "halo")
        .attr("r", d => getNodeRadius(d) + 8)
        .attr("fill", "none")
        .attr("stroke", "#ef4444")
        .attr("stroke-width", 3)  // 增加线宽
        .attr("stroke-dasharray", "5,5")
        .attr("opacity", 0.8);  // 增加不透明度
      
      // 使用D3动画而非SVG animate
      function pulseHalos() {
        highMomentumNodes.selectAll(".halo")
          .transition()
          .duration(1000)
          .attr("r", d => getNodeRadius(d) + 16)  // 增加脉动范围
          .attr("opacity", 0.3)
          .transition()
          .duration(1000)
          .attr("r", d => getNodeRadius(d) + 8)
          .attr("opacity", 0.8)
          .on("end", pulseHalos);
      }
      pulseHalos();
      
      // 2. 中高动量节点轻微缩放脉动（降低阈值）
      const mediumHighNodes = node.filter(d => d.current_momentum && d.current_momentum > 0.4 && d.current_momentum <= 0.6);
      
      function pulseMediumNodes() {
        mediumHighNodes.select("circle")
          .transition()
          .duration(800)
          .attr("r", d => getNodeRadius(d) * 1.2)  // 增加缩放幅度
          .transition()
          .duration(800)
          .attr("r", d => getNodeRadius(d))
          .on("end", pulseMediumNodes);
      }
      pulseMediumNodes();
    }


    // 节点标签
    node.append("text")
      .attr("dy", "0.31em")
      .attr("x", d => (d.value || 10) * 2 + 15)
      .attr("text-anchor", "start")
      .attr("fill", "#e2e8f0")
      .attr("font-size", "13px")
      .attr("font-weight", "500")
      .text(d => d.name);

    // 粒子流动效果（在simulation稳定后启动）
    let particleAnimations = [];
    let particlesInitialized = false;
    
    // 定义粒子初始化函数（在外层作用域）
    const initParticles = () => {
      if (particlesInitialized || !showMomentum) return;
      
      const particleGroup = g.append("g").attr("class", "particles");
      
      // 筛选连接高动量节点的边（降低阈值到0.3）
      const momentumLinks = links.filter(l => {
        const source = l.source;
        const target = l.target;
        const sourceMomentum = parseFloat(source?.current_momentum) || 0;
        const targetMomentum = parseFloat(target?.current_momentum) || 0;
        return (sourceMomentum > 0.3 || targetMomentum > 0.3);
      });
      
      // 为每条边创建粒子
      momentumLinks.forEach((l, idx) => {
        if (idx > 20) return; // 限制粒子数量避免性能问题
        
        const source = l.source;
        const target = l.target;
        
        if (!source || !target || !source.x || !target.x) return;
        
        // 确定粒子流向（从低动量到高动量）
        const sourceMomentum = parseFloat(source.current_momentum) || 0;
        const targetMomentum = parseFloat(target.current_momentum) || 0;
        
        if (sourceMomentum === 0 && targetMomentum === 0) return;
        
        const [from, to] = sourceMomentum < targetMomentum 
          ? [source, target] 
          : [target, source];
        
        // 粒子参数
        const momentumDiff = Math.abs(sourceMomentum - targetMomentum);
        const particleCount = Math.min(Math.ceil(momentumDiff * 8) + 1, 3); // 1-3个粒子
        const duration = Math.max(1500 - (momentumDiff * 800), 800); // 800-1500ms
        
        // 创建多个粒子
        for (let i = 0; i < particleCount; i++) {
          const delay = (duration / particleCount) * i;
          
          const particle = particleGroup.append("circle")
            .attr("r", 2.5)
            .attr("fill", getMomentumColor(Math.max(sourceMomentum, targetMomentum)))
            .attr("opacity", 0)
            .attr("cx", from.x)
            .attr("cy", from.y);
          
          // 粒子动画函数
          function animateParticle() {
            particle
              .attr("cx", from.x)
              .attr("cy", from.y)
              .attr("opacity", 0)
              .transition()
              .delay(delay)
              .duration(100)
              .attr("opacity", 0.9)
              .transition()
              .duration(duration)
              .ease(d3.easeLinear)
              .attr("cx", to.x)
              .attr("cy", to.y)
              .transition()
              .duration(200)
              .attr("opacity", 0)
              .on("end", animateParticle);
          }
          
          animateParticle();
          particleAnimations.push(particle);
        }
      });
      
      particlesInitialized = true;
    };
    
    // 模拟更新
    simulation.on("tick", () => {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

      linkLabel
        .attr("x", d => (d.source.x + d.target.x) / 2)
        .attr("y", d => (d.source.y + d.target.y) / 2);

      node.attr("transform", d => `translate(${d.x},${d.y})`);
      
      // 当simulation稳定后（alpha < 0.05），启动粒子效果
      if (showMomentum && !particlesInitialized && simulation.alpha() < 0.05) {
        initParticles();
      }
    });

    // 拖拽函数
    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    return () => {
      simulation.stop();
    };
  }, [data, dimensions, showEdgeLabels, onNodeClick]);

  return (
    <Card
      ref={containerRef}
      className="d3-graph-card"
      style={isFullscreen ? {
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        zIndex: 9999,
        margin: 0,
        borderRadius: 0,
        background: '#0f172a'
      } : {
        background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
        border: '1px solid #334155'
      }}
      title={title}
      extra={compact ? null : (
        <Space>
          <span style={{ fontSize: '13px', color: '#94a3b8' }}>动量热度</span>
          <Switch 
            checked={showMomentum} 
            onChange={setShowMomentum}
            size="small"
            checkedChildren="开"
            unCheckedChildren="关"
          />
          <span style={{ fontSize: '13px', color: '#94a3b8' }}>显示关系标签</span>
          <Switch 
            checked={showEdgeLabels} 
            onChange={setShowEdgeLabels}
            size="small"
          />
          {allowFullscreen ? (
            <Tooltip title={isFullscreen ? "退出全屏" : "全屏显示"}>
              <Button
                type="text"
                icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
                onClick={toggleFullscreen}
                style={{ color: '#94a3b8' }}
              />
            </Tooltip>
          ) : null}
        </Space>
      )}
    >
      {/* 动量图例 */}
      {showMomentum && showLegend && !compact && (
        <div style={{
          position: 'absolute',
          top: '70px',
          right: '20px',
          background: 'rgba(30, 41, 59, 0.95)',
          border: '1px solid #334155',
          borderRadius: '8px',
          padding: '12px',
          zIndex: 1000,
          backdropFilter: 'blur(8px)',
          fontSize: '12px',
          color: '#e2e8f0'
        }}>
          <div style={{ fontWeight: 'bold', marginBottom: '8px', color: '#f1f5f9' }}>🔥 动量热度图例</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '20px', height: '20px', borderRadius: '50%', background: '#3b82f6' }}></div>
              <span>低热度 (0-30%)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '20px', height: '20px', borderRadius: '50%', background: '#10b981' }}></div>
              <span>中等 (30-50%)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '20px', height: '20px', borderRadius: '50%', background: '#f59e0b' }}></div>
              <span>较高 (50-70%)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '20px', height: '20px', borderRadius: '50%', background: '#ef4444' }}></div>
              <span>高热度 (70-100%)</span>
            </div>
            <div style={{ marginTop: '6px', fontSize: '11px', color: '#94a3b8', fontStyle: 'italic' }}>
              节点大小表示热度强度
            </div>
          </div>
        </div>
      )}

      <div 
        ref={wrapperRef}
        style={{ 
          width: '100%', 
          height: isFullscreen ? 'calc(100vh - 80px)' : `${height}px`,
          borderRadius: '8px',
          overflow: 'hidden'
        }}
      >
        <svg 
          ref={svgRef} 
          width={dimensions.width} 
          height={dimensions.height}
          style={{ background: 'transparent', cursor: 'grab' }}
        />
      </div>
    </Card>
  );
};

export default D3ForceGraph;
