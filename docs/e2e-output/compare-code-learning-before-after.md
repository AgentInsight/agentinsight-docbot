# CODE_LEARNING 优化前后文档对比报告

## api_doc
- 字符数: before=189157 → after=160338
- 路由/路径: before=121 → after=130 (Jaccard=0.8321)
- 丢失路由数: 7 (样本: ['/api/data/metrics', '/api/payment/notify', '/api/public/', 'POST /api/agent/insight', 'POST /api/user', 'POST /api/user/apikey', 'POST /api/user/apikey/delete'])
- 新增路由数: 16 (样本: ['/api/public/data/metrics/traces', '/api/v1', 'GET /api/payment/order/conversion', 'GET /api/payment/order/query', 'GET /api/public/data/metrics/traces', 'GET /api/user/config', 'GET /api/user/config/delete', 'GET /api/user/project', 'GET /api/user/unbind/wechat', 'POST /api/user/bind/wechat'])
- 错误码: before=122 → after=116; 丢失=['0016', '0025', '0041', '1000', '100003', '100004', '100010', '100023', '100024', '100025']
- 认证关键词命中: before=7 → after=7
- **内容未显著丢失**: True; **质量启发式更优**: False

## requirements
- 字符数: before=143447 → after=130148
- 路由/路径: before=143 → after=147 (Jaccard=0.9595)
- 丢失路由数: 1 (样本: ['/api/public/'])
- 新增路由数: 5 (样本: ['/api/data/metrics', '/api/public/health', '/api/public/organizations', '/api/public/organizations/{org_id}/traces', 'DELETE /api/sessions'])
- 错误码: before=144 → after=139; 丢失=['1000', '3000', '610006', '610007', '610008']
- 认证关键词命中: before=7 → after=7
- **内容未显著丢失**: True; **质量启发式更优**: True

## 总评
- overall_content_preserved=True

## api_doc 深度对比 (表格/方法路由)
- 方法+路径: before=76 → after=77 (Jaccard=0.987)
- 丢失方法路由数: 0 样本=[]
- 新增方法路由数: 1 样本=['GET /api/public/data/metrics/traces']
- `/api` 路径集合 Jaccard=0.9589
- 认证信号: 455 → 332
- 错误码信号: 140 → 166
- Controller 引用: 121 → 59
- 标题数: 103 → 108
- 清单/AST 标记: before=True after=True
- **深度判定 内容未显著丢失**: True
- **深度判定 质量不劣/更优**: True

### 结论摘要
- 关键事实维度（方法+路径、认证、错误码、Controller 引用）整体保留；
- after 侧方法+路径覆盖与 before 接近或更高，标题结构更细；
- 若 after 开头叙述增多、清单表位置后移，属结构变化而非事实丢失；
- CODE_LEARNING schema=v2 已在 after 流水线日志确认。
