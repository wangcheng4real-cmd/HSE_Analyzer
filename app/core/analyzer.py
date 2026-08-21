from app.core.brake.brake_analyzer import BrakeAnalyzer
from app.core.brake.brake_data_loader import BrakeDataLoader
from app.core.hazard.hazard_data_loader import HazardDataLoader
from app.core.hazard.hazard_analyzer import HazardAnalyzer
from app.core.risk.risk_analyzer import RiskAnalyzer


class Analyzer:

    def __init__(self, cfg):
        self.cfg = cfg

        # 隐患模块：保留原有名称，避免影响hazard_page.py
        self.loader = HazardDataLoader()
        self.hazard = HazardAnalyzer(cfg)

        # 预警刹车模块：文件和数据完全独立
        self.brake_loader = BrakeDataLoader()
        self.brake = BrakeAnalyzer()

        self.risk = RiskAnalyzer(cfg)
