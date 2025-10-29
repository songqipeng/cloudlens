# Redis价格API分析文档

## 需要查看的官方文档

### 1. DescribePrice API文档
- **文档地址**: https://help.aliyun.com/zh/redis/developer-reference/api-r-kvstore-2015-01-01-describeprice-redis
- **关键点**: 
  - 请求参数说明
  - 响应字段结构
  - OrderType参数（RENEW vs BUY）的区别
  - Period参数的含义（1 = 1个月，还是按天计算？）

### 2. 官网价格直降活动文档
- **关键信息**: 自2024年2月29日起，Tair实施了"官网价格直降"优惠活动
- **影响**: 
  - 售卖页和控制台自动享受新官网折扣价
  - 续费时自动抵扣未履约时段差价
  - **API返回的可能已经是折扣后的价格，而非原始基准价**

### 3. 价格查询相关的响应字段
- **Order字段**:
  - `OriginalAmount`: 原价
  - `TradeAmount`: 实付价
  - `StandPrice`: 标准价/列表价
  - `DiscountAmount`: 折扣金额
  
- **SubOrders.SubOrder字段**:
  - `OriginalAmount`: 子订单原价
  - `TradeAmount`: 子订单实付价
  - `StandPrice`: 子订单标准价
  - `DepreciateInfo.ListPrice`: 列表价格（可能包含基准价）

- **ModuleInstance字段**:
  - `StandPrice`: 模块标准价
  - `TotalProductFee`: 模块总产品费用（可能包含原价）
  - `PayFee`: 模块实付费用
  - `PricingModule`: 是否为计价模块

## 问题分析

### 当前API返回的数据
- `Order.TradeAmount` = 0.161
- `Order.OriginalAmount` = 0.161
- `ModuleInstance`累加 = 16.1（分片14.0 + 存储2.1）
- **实际需要的**: 基准价76.98元/月，续费价38.49元

### 可能的原因
1. **官网价格直降活动**: API返回的`StandPrice`或`OriginalAmount`可能已经是直降后的价格
2. **PriceUnit问题**: `Period=1`可能不是指1个月，需要确认单位
3. **字段理解错误**: 可能需要使用`DepreciateInfo.ListPrice`作为基准价
4. **BUY vs RENEW**: BUY方式返回的是新购价格，可能不包含续费折扣

## 修复建议

### 方案1: 检查DepreciateInfo.ListPrice
```python
# 在SubOrder中查找DepreciateInfo.ListPrice
if 'DepreciateInfo' in sub_order:
    list_price = sub_order['DepreciateInfo'].get('ListPrice', 0)
    if list_price > 0:
        # 这可能包含基准价（76.98）
```

### 方案2: 使用StandPrice作为基准价
```python
# StandPrice可能是标准定价
if 'StandPrice' in order and order['StandPrice'] > 0:
    original_price = order['StandPrice']
```

### 方案3: 查看API响应中的Rules字段
```python
# Rules字段可能包含折扣规则
if 'Rules' in data and 'Rule' in data['Rules']:
    # 解析折扣规则
```

### 方案4: 查询价格表API
- 可能需要使用其他API查询官方定价表
- 或维护一个价格对照表

