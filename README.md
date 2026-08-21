# HSE 数据分析平台

基于 Tkinter、pandas 和 Matplotlib 的本地 HSE 数据分析工具，包含隐患分析、预警刹车分析及综合分析预留模块。

## 环境

- Python 3.9+
- Windows（界面针对 Microsoft YaHei 和 Windows DPI 做了适配）

```powershell
py -3.9 -m pip install -r requirements.txt
```

## 启动

```powershell
py -3.9 main.py
```

## 数据要求

### 隐患数据

上传一个或多个字段结构一致的 Excel。必须包含 `检查日期`，系统会排除无法解析日期的记录，并支持：

- 按周：周一至周日；
- 按月：自然月；
- 按季度：自然季度（1–3月、4–6月、7–9月、10–12月）。

### 预警刹车数据

支持通报批评、整改通知、挂牌督办、管理约谈和停工令。系统根据表头、Sheet、文件名及编号特征识别类型并统一字段。

## 目录

```text
app/ui/pages/        Tkinter 页面布局与文件管理
app/ui/controllers/  分析弹窗、结果转换与绘图交互
app/ui/components/   通用滚动弹窗、文件表格和仪表盘组件
app/core/hazard/     隐患配置、文件读取、筛选及分析服务
app/core/brake/      预警刹车分析服务
app/charts/          Matplotlib 图表及字体配置
tests/               unittest 自动化测试
```

## 测试

```powershell
py -3.9 -m unittest discover -s tests -v
```

测试使用运行时创建的临时 Excel，不需要提交真实业务数据。
