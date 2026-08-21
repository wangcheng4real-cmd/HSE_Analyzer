from app.ui.main_window import run_app

if __name__ == "__main__":
    run_app()

"""
HSE 数据分析平台程序入口及目录说明
==================================

启动方式：
    python main.py

项目目录：

main.py
    程序唯一启动入口，只负责调用 app.ui.main_window.run_app()。

app/
    应用源代码目录。

    charts/
        Matplotlib 图表生成层，不处理业务数据和 Tkinter 页面逻辑。

        chart.py
            ChartFactory 图表工厂，统一生成柱状图、饼图和折线图 Figure。
        font_config.py
            配置 Matplotlib 中文字体，避免中文标题和坐标显示乱码。

    core/
        核心业务层，负责数据状态、后台任务、Excel 加载、筛选和统计。

        analyzer.py
            总分析器入口，组装隐患分析器、预警刹车分析器及各自加载器。
        analysis_state.py
            保存模块当前 DataFrame、周期、加载状态、数据版本和分析缓存。
        background_task.py
            单后台任务执行器；工作线程负责计算，结果通过主线程回调更新 UI。

        hazard/
            隐患分析业务模块。

            hazard_config.py
                集中定义隐患 Excel 字段名、流程值和派生字段名。
            hazard_data_loader.py
                读取隐患 Excel、校验检查日期，并按周/月/季度进行分组。
            hazard_filter.py
                执行隐患公共业务筛选，例如状态过滤。
            hazard_preprocessor.py
                统一完成列名、文本、流程、区域和隐患分类预处理。
            hazard_analyzer.py
                隐患分析统一接口，组装并调用下面的各项统计服务。
            results.py
                定义趋势点、单序列趋势和多序列趋势等标准结果对象。
            level_service.py
                隐患等级统计。
            unit_service.py
                责任单位总体数量统计。
            category_service.py
                隐患大类和二级分类统计。
            area_service.py
                区域总体数量统计。
            interface_service.py
                接口队办统计。
            ab_level_service.py
                A/B 级隐患分类统计。
            trend_service.py
                隐患总体周期趋势统计。
            ab_trend_service.py
                A/B 级隐患周期趋势统计。
            unit_profile_service.py
                单位隐患类别画像统计。
            unit_ab_service.py
                指定单位的 A/B 类隐患统计。
            unit_team_service.py
                指定单位的多发责任班组统计。
            unit_verify_service.py
                各单位按期验证率统计。
            unit_trend_service.py
                指定单位的隐患周期趋势统计。
            area_profile_service.py
                区域隐患类别画像统计。
            area_ab_service.py
                指定区域的 A/B 类隐患统计。
            area_trend_service.py
                指定区域的隐患周期趋势统计。
            special_trend_service.py
                指定二级隐患分类的总体专项趋势统计。
            special_unit_trend_service.py
                指定二级隐患分类在各单位的专项趋势统计。
            special_area_trend_service.py
                指定二级隐患分类在各区域的专项趋势统计。

        brake/
            预警刹车分析业务模块。

            __init__.py
                标记 brake 为 Python 包。
            brake_data_loader.py
                识别并读取五类预警刹车 Excel，统一单位与发出日期字段。
            brake_filter.py
                统一执行预警刹车状态过滤、类型筛选和编号去重。
            brake_period.py
                生成周、月、季度的周期开始日期、完整时间轴和显示文本。
            brake_analyzer.py
                预警刹车分析统一接口，组装并调用各项统计服务。
            brake_overall_service.py
                预警类型、单位 Top10、问题类别及总体趋势统计。
            brake_unit_profile_service.py
                单位问题类别和单位周期趋势统计。
            brake_special_trend_service.py
                问题类别总体专项趋势及单位专项趋势统计。

    ui/
        Tkinter 用户界面层，只负责页面交互、任务提交和结果展示。

        main_window.py
            创建主窗口、品牌导航、页面容器、运行日志、状态栏和任务管理器。
        theme.py
            集中定义颜色、字体、ttk 样式、面板、按钮和功能卡片。

        pages/
            三个主业务页面。

            __init__.py
                标记 pages 为 Python 包。
            hazard_page.py
                隐患分析页面，包括文件管理、周期选择和分析卡片布局。
            brake_page.py
                预警刹车页面，包括文件管理、周期选择和分析卡片布局。
            risk_page.py
                综合分析页面，目前展示建设中状态。

        controllers/
            页面业务交互控制器，将后台统计结果转换为弹窗或图表。

            __init__.py
                标记 controllers 为 Python 包。
            hazard_analysis_controller.py
                处理所有隐患分析按钮、选择窗口、后台统计和出图回调。
            brake_analysis_controller.py
                处理所有预警刹车分析按钮、选择窗口、后台统计和出图回调。
            chart_controller_mixin.py
                为控制器提供统一的柱状图、饼图和折线图显示方法。

        components/
            可复用的 Tkinter UI 组件。

            __init__.py
                标记 components 为 Python 包。
            chart_window.py
                承载 Matplotlib 图表和工具栏的统一窗口。
            dashboard_panel.py
                根据分组声明批量生成仪表盘功能卡片。
            file_table.py
                创建隐患和预警刹车共用的文件 Treeview 表格。
            ranked_selection_dialog.py
                数量排序、搜索和卡片选择共用弹窗，支持单位、区域和分类。
            scrollable_dialog.py
                创建通用的可滚动辅助弹窗。

tests/
    基于 unittest 的自动化测试目录；测试数据运行时动态构造，不保存业务 Excel。

    __init__.py
        标记 tests 为 Python 测试包。
    test_analysis_state.py
        测试模块数据状态、周期和清空行为。
    test_background_and_cache.py
        测试后台线程、重复任务锁、取消加载和缓存失效。
    test_brake_loader.py
        测试预警刹车类型识别、字段映射、单位归并和文件错误。
    test_brake_special_trend.py
        测试预警刹车问题类别专项趋势和单位专项趋势。
    test_chart_factory.py
        测试图表工厂能够正确创建各类 Figure。
    test_hazard_data_loader.py
        测试隐患 Excel 加载、日期校验和多文件合并。
    test_hazard_preprocessor.py
        测试隐患字段清洗、区域提取和两种分类口径。
    test_hazard_results.py
        测试标准趋势结果对象及旧接口转换。
    test_hazard_services.py
        测试隐患总体、画像、趋势和专项统计服务。
    test_period_grouping.py
        测试周、月、季度边界和周期切换数据总量。
    test_ranked_selection_dialog.py
        测试选择弹窗的数量排序和搜索过滤逻辑。
    test_smoke_imports.py
        测试主要模块导入、页面入口和核心接口未丢失。
"""

